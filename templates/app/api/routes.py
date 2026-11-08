"""__NAME__ back end. Routes are served at /api/__ID__/... by the Nook.

Bricks you'll probably want (see the nook-app skill):
  from nookkit.store import Database       SQLite + migrations
  from nookkit.auth import Accounts        sign up / log in / sessions
  from nookkit.files import decode_upload  safe uploads
  from nookkit.jobs import Job             one background task with live progress
  from nookkit.paths import data_dir       ~/.local/share/nook/__ID__/
"""


def hello(req):
    return req.json({"hello": "from __NAME__", "from_phone": req.remote})


ROUTES = {
    "GET /hello": hello,
}
