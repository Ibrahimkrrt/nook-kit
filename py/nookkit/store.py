"""SQLite with numbered migrations, safe to share between the hub's threads.

    db = Database(data_dir("burrow") / "burrow.db", migrations=[
        "CREATE TABLE docs (...)",              # 1
        "ALTER TABLE docs ADD COLUMN note TEXT" # 2  (never edit an old one: append)
    ])
    db.all("SELECT * FROM docs WHERE user_id = ?", (uid,))
"""
import sqlite3
import threading


class Database:
    def __init__(self, path, migrations=()):
        self.path = path
        self._lock = threading.RLock()
        self.con = sqlite3.connect(path, check_same_thread=False)
        self.con.row_factory = sqlite3.Row
        self.con.execute("PRAGMA foreign_keys = ON")
        self.con.execute("PRAGMA journal_mode = WAL")
        try:
            path.chmod(0o600)
        except (AttributeError, OSError):
            pass
        self.migrate(migrations)

    def migrate(self, migrations):
        with self._lock:
            have = self.con.execute("PRAGMA user_version").fetchone()[0]
            for n, sql in enumerate(migrations, start=1):
                if n <= have:
                    continue
                self.con.executescript(f"BEGIN; {sql}; PRAGMA user_version = {n}; COMMIT;")

    def ensure(self, sql):
        """Idempotent schema owned by a brick (e.g. auth): CREATE … IF NOT EXISTS statements."""
        with self._lock:
            self.con.executescript(sql)

    def run(self, sql, args=()):
        """Write; returns lastrowid."""
        with self._lock:
            cur = self.con.execute(sql, args)
            self.con.commit()
            return cur.lastrowid

    def all(self, sql, args=()):
        with self._lock:
            return self.con.execute(sql, args).fetchall()

    def one(self, sql, args=()):
        with self._lock:
            return self.con.execute(sql, args).fetchone()
