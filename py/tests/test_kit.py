import base64
import json
import tempfile
import time
import unittest
from pathlib import Path

import nookkit
from nookkit import auth, files, jobs, semver, store
from nookkit.http import Request


def req(body=None, cookie=None, method="POST"):
    headers = {"Cookie": cookie} if cookie else {}
    return Request(method, "/", {}, body or {}, False, headers)


def cookie_of(resp):
    raw = resp[1].get("Set-Cookie", "")
    return raw.split(";")[0]


class VersionTest(unittest.TestCase):
    def test_py_and_js_versions_match(self):
        pkg = json.loads((Path(__file__).parents[2] / "package.json").read_text())
        self.assertEqual(pkg["version"], nookkit.__version__)


class SemverTest(unittest.TestCase):
    def test_ranges(self):
        self.assertTrue(semver.satisfies("1.4.2", "^1.0.0"))
        self.assertFalse(semver.satisfies("2.0.0", "^1.0.0"))
        self.assertFalse(semver.satisfies("0.9.0", "^1.0.0"))
        self.assertTrue(semver.satisfies("1.2.9", "~1.2.0"))
        self.assertFalse(semver.satisfies("1.3.0", "~1.2.0"))
        self.assertTrue(semver.satisfies("3.0.0", ">=1.0.0"))
        self.assertTrue(semver.satisfies("1.0.0", "*"))


class StoreTest(unittest.TestCase):
    def test_migrations_run_once_and_in_order(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "t.db"
            db = store.Database(p, ["CREATE TABLE a (x INTEGER)"])
            db.run("INSERT INTO a VALUES (1)")
            db = store.Database(p, ["CREATE TABLE a (x INTEGER)", "ALTER TABLE a ADD COLUMN y TEXT"])
            self.assertEqual(db.one("PRAGMA user_version")[0], 2)
            self.assertEqual(db.one("SELECT x, y FROM a")[0], 1)


class AuthTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = store.Database(Path(self.tmp.name) / "a.db")
        self.acc = auth.Accounts(self.db, "demo", max_fails=3)
        self.acc._fail_delay = 0

    def tearDown(self):
        self.tmp.cleanup()

    def test_signup_login_logout(self):
        r = self.acc.signup(req({"username": "Ibra", "password": "correct horse"}))
        self.assertEqual(r[0], 200)
        c = cookie_of(r)
        self.assertTrue(c.startswith("demo_sid="))
        self.assertIn("Path=/api/demo", r[1]["Set-Cookie"])
        self.assertIn("HttpOnly", r[1]["Set-Cookie"])
        me = json.loads(self.acc.me(req(cookie=c, method="GET"))[2])
        self.assertEqual(me["user"]["username"], "ibra")
        self.acc.logout(req(cookie=c))
        me = json.loads(self.acc.me(req(cookie=c, method="GET"))[2])
        self.assertIsNone(me["user"])

    def test_rejects_bad_input_and_duplicates(self):
        self.assertEqual(self.acc.signup(req({"username": "ab", "password": "12345678"}))[0], 400)
        self.assertEqual(self.acc.signup(req({"username": "abc", "password": "short"}))[0], 400)
        self.acc.signup(req({"username": "abc", "password": "12345678"}))
        self.assertEqual(self.acc.signup(req({"username": "ABC", "password": "12345678"}))[0], 400)

    def test_password_hash_not_stored_plain(self):
        self.acc.signup(req({"username": "abc", "password": "12345678"}))
        row = self.db.one("SELECT pw_hash FROM users")
        self.assertNotIn(b"12345678", bytes(row["pw_hash"]))

    def test_lockout(self):
        self.acc.signup(req({"username": "abc", "password": "12345678"}))
        auth.time.sleep, real = (lambda s: None), auth.time.sleep
        try:
            for _ in range(3):
                self.assertEqual(self.acc.login(req({"username": "abc", "password": "nope"}))[0], 401)
            self.assertEqual(self.acc.login(req({"username": "abc", "password": "12345678"}))[0], 429)
        finally:
            auth.time.sleep = real

    def test_required_and_isolation(self):
        a = cookie_of(self.acc.signup(req({"username": "aaa", "password": "12345678"})))
        route = self.acc.required(lambda r, u: r.json({"id": u["id"]}))
        self.assertEqual(route(req(method="GET"))[0], 401)
        self.assertEqual(route(req(cookie=a, method="GET"))[0], 200)
        self.assertEqual(route(req(cookie="demo_sid=forged", method="GET"))[0], 401)

    def test_change_password_signs_out_other_devices(self):
        a = cookie_of(self.acc.signup(req({"username": "aaa", "password": "12345678"})))
        b = cookie_of(self.acc.login(req({"username": "aaa", "password": "12345678"})))
        change = self.acc.routes()["POST /password"]
        self.assertEqual(change(req({"old": "wrong", "new": "abcdefgh"}, cookie=a))[0], 401)
        self.assertEqual(change(req({"old": "12345678", "new": "abcdefgh"}, cookie=a))[0], 200)
        me = lambda c: json.loads(self.acc.me(req(cookie=c, method="GET"))[2])["user"]
        self.assertIsNotNone(me(a))
        self.assertIsNone(me(b))


class FilesTest(unittest.TestCase):
    def b64(self, raw):
        return base64.b64encode(raw).decode()

    def test_accepts_real_pdf(self):
        data, ext = files.decode_upload(self.b64(b"%PDF-1.4 hi"), "x.PDF")
        self.assertEqual(ext, ".pdf")
        self.assertEqual(data, b"%PDF-1.4 hi")

    def test_rejects(self):
        with self.assertRaises(files.UploadError):
            files.decode_upload(self.b64(b"<html>"), "x.pdf")          # fake pdf
        with self.assertRaises(files.UploadError):
            files.decode_upload(self.b64(b"%PDF"), "x.html")            # wrong type
        with self.assertRaises(files.UploadError):
            files.decode_upload("not base64!!", "x.pdf")
        with self.assertRaises(files.UploadError):
            files.decode_upload(self.b64(b"%PDF" + b"0" * 2000), "x.pdf", max_bytes=1000)

    def test_safe_name_and_unique(self):
        self.assertEqual(files.safe_name("../../etc/Février paie?.pdf"), "etc_Fevrier paie_.pdf")
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "a.pdf").write_bytes(b"1")
            self.assertEqual(files.unique_path(d, "a.pdf").name, "a (2).pdf")
            self.assertTrue(files.inside(Path(d) / "a.pdf", d))
            self.assertFalse(files.inside(Path(d) / ".." / "x", d))


class JobsTest(unittest.TestCase):
    def test_one_at_a_time_and_errors_surface(self):
        job = jobs.Job(status="idle", percent=0)

        def slow(j):
            j.update(status="working", percent=50)
            time.sleep(0.2)
            j.update(status="done", percent=100)

        self.assertTrue(job.start(slow))
        self.assertFalse(job.start(slow))
        time.sleep(0.35)
        self.assertEqual(job.snapshot()["status"], "done")

        def boom(j):
            raise RuntimeError("kaput")
        self.assertTrue(job.start(boom))
        time.sleep(0.1)
        s = job.snapshot()
        self.assertEqual((s["status"], s["message"], s["seq"]), ("error", "kaput", 2))


if __name__ == "__main__":
    unittest.main()


class LLMTest(unittest.TestCase):
    """nookkit.llm against a fake Ollama on a random local port."""

    @classmethod
    def setUpClass(cls):
        import os
        import threading
        from http.server import BaseHTTPRequestHandler, HTTPServer

        seen = cls.seen = []

        class Fake(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def reply(self, obj):
                body = json.dumps(obj).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                self.reply({"models": [{"name": "tiny:1b", "model": "tiny:1b"}]})

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                seen.append(body)
                self.reply({"message": {"role": "assistant", "content": json.dumps({"folder": "Taxes/2024"})}})

        cls.server = HTTPServer(("127.0.0.1", 0), Fake)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.old = {k: os.environ.get(k) for k in ("NOOK_LLM_URL", "NOOK_LLM_MODEL")}
        os.environ["NOOK_LLM_URL"] = f"http://127.0.0.1:{cls.server.server_port}"
        os.environ["NOOK_LLM_MODEL"] = "tiny:1b"

    @classmethod
    def tearDownClass(cls):
        import os
        cls.server.shutdown()
        for k, v in cls.old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_status_and_ask(self):
        from nookkit import llm
        st = llm.status(max_age=0)
        self.assertTrue(st["running"] and st["ready"], st)
        out = llm.ask_json("where?", {"type": "object"}, system="be brief")
        self.assertEqual(out, {"folder": "Taxes/2024"})
        sent = self.seen[-1]
        self.assertEqual(sent["model"], "tiny:1b")
        self.assertEqual(sent["format"], {"type": "object"})
        self.assertEqual(sent["messages"][0]["role"], "system")

    def test_refuses_non_local_urls(self):
        from nookkit import llm
        self.assertTrue(llm.is_local("http://localhost:11434"))
        self.assertTrue(llm.is_local("http://[::1]:11434"))
        self.assertFalse(llm.is_local("http://192.168.1.20:11434"))
        self.assertFalse(llm.is_local("https://api.example.com"))
        self.assertFalse(llm.is_local("file:///etc/passwd"))

    def test_unreachable_is_not_ready(self):
        import os
        from nookkit import llm
        os.environ["NOOK_LLM_URL"] = "http://127.0.0.1:9"
        try:
            st = llm.status(max_age=0)
            self.assertFalse(st["running"])
            with self.assertRaises(llm.LLMError):
                llm.ask_json("x", {"type": "object"})
        finally:
            os.environ["NOOK_LLM_URL"] = f"http://127.0.0.1:{self.server.server_port}"


class ExtractTextTest(unittest.TestCase):
    def test_unknown_types_give_empty_text(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.txt"
            p.write_text("hello")
            self.assertEqual(files.extract_text(p), "")
            self.assertEqual(files.extract_text(Path(d) / "missing.pdf"), "")
