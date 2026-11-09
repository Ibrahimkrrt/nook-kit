"""nookkit: back-end bricks shared by every Nook app.

The Nook (the hub) puts this package on the import path and hands each app a `Request`.
An app's api/routes.py exports  ROUTES = {"GET /status": fn, "POST /do": fn}  where fn(req) returns
req.json(...), req.error(...) or req.file(...).

Bricks:
  nookkit.http    Request / responses (the contract between the hub and apps)
  nookkit.paths   where an app keeps its data
  nookkit.store   SQLite with numbered migrations
  nookkit.auth    accounts + sessions (sign up, log in, cookie, rate limit)
  nookkit.files   safe uploads: base64 decode, size limit, type sniffing, safe names
  nookkit.jobs    one background job with live progress (download, convert, …)
  nookkit.llm     optional local language model (Ollama, loopback only) with JSON answers
  nookkit.semver  "does kit 1.2.0 satisfy ^1.0.0?"
"""
__version__ = "1.1.0"
