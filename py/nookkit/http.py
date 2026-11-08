"""The request/response contract between the Nook and its apps.

A route is fn(req) -> (status, headers, body). body is bytes, or a Path (streamed by the hub).
"""
import json
import mimetypes
import urllib.parse
from http import cookies
from pathlib import Path


class Request:
    def __init__(self, method, path, query, body, remote, headers=None):
        self.method = method      # "GET" | "POST"
        self.path = path          # "/status" (the part after /api/<app>)
        self.query = query        # {"id": "3"}
        self.body = body          # parsed JSON for POST, {} for GET
        self.remote = remote      # True when it comes from another device (a phone)
        self.headers = headers or {}

    # ---- reading ----
    def cookie(self, name):
        c = cookies.SimpleCookie(self.headers.get("Cookie", ""))
        return c[name].value if name in c else None

    def str(self, key, default="", max_len=2000):
        """A string field from the JSON body, trimmed and length-capped."""
        return str(self.body.get(key, default) or default).strip()[:max_len]

    # ---- responses ----
    @staticmethod
    def json(obj, code=200, headers=None):
        return code, {"Content-Type": "application/json", "Cache-Control": "no-store", **(headers or {})}, json.dumps(obj).encode()

    @staticmethod
    def error(msg, code=400):
        return Request.json({"error": msg}, code)

    @staticmethod
    def file(path, download_name=None, inline=False, content_type=None):
        path = Path(path)
        ctype = content_type or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        headers = {"Content-Type": ctype, "X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"}
        if download_name:
            how = "inline" if inline else "attachment"
            headers["Content-Disposition"] = f"{how}; filename*=UTF-8''{urllib.parse.quote(download_name)}"
        return 200, headers, path


def with_headers(resp, **extra):
    """Add headers to a response tuple: with_headers(req.json(...), **{"Set-Cookie": c})"""
    code, headers, body = resp
    return code, {**headers, **extra}, body
