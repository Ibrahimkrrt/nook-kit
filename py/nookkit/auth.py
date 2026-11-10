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
  * optional inactivity logout: Accounts(db, "burrow", idle_minutes=15). A session unused for that long
    (plus a short grace for the browser's heartbeat) is deleted on the server, whatever the browser does.
    Each user can pick their own delay from IDLE_CHOICES (POST /session/idle); the browser keeps the
    session alive while the person is actually using the page (POST /session/alive).
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
IDLE_CHOICES = (5, 10, 15, 30, 60)   # minutes a user can pick
IDLE_GRACE = 75                      # seconds: the browser pings at most every 30 s, and logs out first
TOUCH_EVERY = 15                     # seconds between last_seen writes

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
    def __init__(self, db, app_id, session_days=30, max_fails=8, lock_seconds=600, idle_minutes=None):
        self.db = db
        self.cookie = f"{app_id}_sid"
        self.path = f"/api/{app_id}"
        self.max_age = session_days * 86400
        self.max_fails, self.lock_seconds = max_fails, lock_seconds
        self._fails = {}
        self._fails_lock = threading.Lock()
        self.idle_default = idle_minutes
        db.ensure(SCHEMA)
        # columns added after 1.0 (bricks own their schema, so they upgrade it themselves)
        self._add_column("sessions", "last_seen", "REAL")
        self._add_column("users", "idle_minutes", "INTEGER")

    def _add_column(self, table, name, decl):
        if name not in {r["name"] for r in self.db.all(f"PRAGMA table_info({table})")}:
            self.db.ensure(f"ALTER TABLE {table} ADD COLUMN {name} {decl}")

    # ---------- helpers ----------
    def _cookie(self, token, max_age=None):
        age = self.max_age if max_age is None else max_age
        return f"{self.cookie}={token}; Path={self.path}; Max-Age={age}; HttpOnly; SameSite=Lax"

    def _start_session(self, user_id):
        token = secrets.token_urlsafe(32)
        now = time.time()
        self.db.run("DELETE FROM sessions WHERE expires < ?", (now,))
        self.db.run("INSERT INTO sessions (token_hash, user_id, expires, last_seen) VALUES (?, ?, ?, ?)",
                    (_token_hash(token), user_id, now + self.max_age, now))
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

    def idle_seconds(self, user):
        """This user's inactivity limit in seconds, or None when the app doesn't log out idle sessions."""
        if not self.idle_default:
            return None
        return int((user["idle_minutes"] or self.idle_default) * 60)

    def public(self, user):
        out = {"username": user["username"], "display": user["display"]}
        if self.idle_default:
            out["idle"] = self.idle_seconds(user)
            out["idle_choices"] = list(IDLE_CHOICES)
        return out

    def current(self, req, touch=True):
        token = req.cookie(self.cookie)
        if not token:
            return None
        now, th = time.time(), _token_hash(token)
        row = self.db.one(
            """SELECT u.id, u.username, u.display, u.idle_minutes, s.last_seen FROM sessions s JOIN users u ON u.id = s.user_id
               WHERE s.token_hash = ? AND s.expires > ?""", (th, now))
        if not row:
            return None
        idle = self.idle_seconds(row)
        if idle and row["last_seen"] and now - row["last_seen"] > idle + IDLE_GRACE:
            self.db.run("DELETE FROM sessions WHERE token_hash = ?", (th,))
            return None
        if touch and (not row["last_seen"] or now - row["last_seen"] > TOUCH_EVERY):
            self.db.run("UPDATE sessions SET last_seen = ? WHERE token_hash = ?", (now, th))
        return row

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
        user = self.db.one("SELECT id, username, display, idle_minutes FROM users WHERE id = ?", (uid,))
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

    def alive(self, req, user):
        """Heartbeat from a page the person is using (reading counts, even without requests)."""
        return req.json({"ok": True, "idle": self.idle_seconds(user)})

    def set_idle(self, req, user):
        try:
            minutes = int(req.body.get("minutes"))
        except (TypeError, ValueError):
            minutes = 0
        if minutes not in IDLE_CHOICES:
            return req.error(f"Pick one of {', '.join(map(str, IDLE_CHOICES))} minutes")
        self.db.run("UPDATE users SET idle_minutes = ? WHERE id = ?", (minutes, user["id"]))
        return req.json({"idle": minutes * 60})

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
            **({"POST /session/alive": self.required(self.alive),
                "POST /session/idle": self.required(self.set_idle)} if self.idle_default else {}),
        }
