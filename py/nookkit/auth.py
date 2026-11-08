"""Accounts brick: sign up, log in, log out, change password, and a @required decorator.

    accounts = Accounts(db, "burrow")
    ROUTES = {**accounts.routes(), "GET /docs": accounts.required(list_docs)}
    def list_docs(req, user): ...            # user = {"id", "username", "display"}

Security choices (don't weaken them in an app):
  * scrypt password hashes with a per-user salt, compared in constant time
  * session token = 32 random bytes; only its SHA-256 is stored
  * cookie: HttpOnly, SameSite=Lax, Path=/api/<app> (so apps never see each other's sessions)
  * 8 wrong passwords for a username → 10 minute pause; every failure costs 0.5 s
  * CSRF is covered by the hub: POSTs must be JSON and come from a known Origin
"""
import hashlib
import hmac
import re
import secrets
import threading
import time

from .http import with_headers

USERNAME = re.compile(r"^[a-z0-9_.-]{3,24}$")
MIN_PASSWORD = 8

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    display TEXT NOT NULL,
    pw_salt BLOB NOT NULL,
    pw_hash BLOB NOT NULL,
    created REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires REAL NOT NULL
);
"""


def hash_password(password, salt):
    return hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)


def _token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


class Accounts:
    def __init__(self, db, app_id, session_days=30, max_fails=8, lock_seconds=600):
        self.db = db
        self.cookie = f"{app_id}_sid"
        self.path = f"/api/{app_id}"
        self.max_age = session_days * 86400
        self.max_fails, self.lock_seconds = max_fails, lock_seconds
        self._fails = {}
        self._fails_lock = threading.Lock()
        db.ensure(SCHEMA)

    # ---------- helpers ----------
    def _cookie(self, token, max_age=None):
        age = self.max_age if max_age is None else max_age
        return f"{self.cookie}={token}; Path={self.path}; Max-Age={age}; HttpOnly; SameSite=Lax"

    def _start_session(self, user_id):
        token = secrets.token_urlsafe(32)
        now = time.time()
        self.db.run("DELETE FROM sessions WHERE expires < ?", (now,))
        self.db.run("INSERT INTO sessions VALUES (?, ?, ?)", (_token_hash(token), user_id, now + self.max_age))
        return self._cookie(token)

    def _locked(self, username):
        with self._fails_lock:
            count, since = self._fails.get(username, (0, 0))
            if time.time() - since > self.lock_seconds:
                self._fails.pop(username, None)
                return False
            return count >= self.max_fails

    def _fail(self, username):
        with self._fails_lock:
            count, since = self._fails.get(username, (0, time.time()))
            self._fails[username] = (count + 1, since)

    @staticmethod
    def public(user):
        return {"username": user["username"], "display": user["display"]}

    def current(self, req):
        token = req.cookie(self.cookie)
        if not token:
            return None
        return self.db.one(
            """SELECT u.id, u.username, u.display FROM sessions s JOIN users u ON u.id = s.user_id
               WHERE s.token_hash = ? AND s.expires > ?""", (_token_hash(token), time.time()))

    def required(self, fn):
        """Decorator: fn(req, user); answers 401 when nobody is logged in."""
        def wrapped(req):
            user = self.current(req)
            if not user:
                return req.error("please log in", 401)
            return fn(req, user)
        wrapped.__name__ = getattr(fn, "__name__", "route")
        return wrapped

    # ---------- routes ----------
    def me(self, req):
        user = self.current(req)
        return req.json({"user": self.public(user) if user else None})

    def signup(self, req):
        username = req.str("username").lower()
        display = req.str("display", max_len=32) or username
        password = str(req.body.get("password", ""))
        if not USERNAME.match(username):
            return req.error("Usernames are 3–24 characters: letters, numbers, . _ or -")
        if len(password) < MIN_PASSWORD:
            return req.error(f"Passwords need at least {MIN_PASSWORD} characters")
        if self.db.one("SELECT 1 FROM users WHERE username = ?", (username,)):
            return req.error("That username is already taken")
        salt = secrets.token_bytes(16)
        uid = self.db.run(
            "INSERT INTO users (username, display, pw_salt, pw_hash, created) VALUES (?, ?, ?, ?, ?)",
            (username, display, salt, hash_password(password, salt), time.time()))
        user = self.db.one("SELECT id, username, display FROM users WHERE id = ?", (uid,))
        return with_headers(req.json({"user": self.public(user)}), **{"Set-Cookie": self._start_session(uid)})

    def login(self, req):
        username = req.str("username").lower()
        password = str(req.body.get("password", ""))
        if self._locked(username):
            return req.error("Too many tries. Take a 10 minute break.", 429)
        user = self.db.one("SELECT * FROM users WHERE username = ?", (username,))
        if not user or not hmac.compare_digest(hash_password(password, user["pw_salt"]), user["pw_hash"]):
            self._fail(username)
            time.sleep(0.5)
            return req.error("Wrong username or password", 401)
        with self._fails_lock:
            self._fails.pop(username, None)
        return with_headers(req.json({"user": self.public(user)}), **{"Set-Cookie": self._start_session(user["id"])})

    def logout(self, req):
        if token := req.cookie(self.cookie):
            self.db.run("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),))
        return with_headers(req.json({"ok": True}), **{"Set-Cookie": self._cookie("", 0)})

    def change_password(self, req, user):
        old, new = str(req.body.get("old", "")), str(req.body.get("new", ""))
        row = self.db.one("SELECT pw_salt, pw_hash FROM users WHERE id = ?", (user["id"],))
        if not hmac.compare_digest(hash_password(old, row["pw_salt"]), row["pw_hash"]):
            return req.error("Your current password is wrong", 401)
        if len(new) < MIN_PASSWORD:
            return req.error(f"Passwords need at least {MIN_PASSWORD} characters")
        salt = secrets.token_bytes(16)
        self.db.run("UPDATE users SET pw_salt = ?, pw_hash = ? WHERE id = ?", (salt, hash_password(new, salt), user["id"]))
        # sign out every other device, keep this one
        self.db.run("DELETE FROM sessions WHERE user_id = ? AND token_hash != ?",
                    (user["id"], _token_hash(req.cookie(self.cookie) or "")))
        return req.json({"ok": True})

    def routes(self):
        return {
            "GET /me": self.me,
            "POST /signup": self.signup,
            "POST /login": self.login,
            "POST /logout": self.logout,
            "POST /password": self.required(self.change_password),
        }
