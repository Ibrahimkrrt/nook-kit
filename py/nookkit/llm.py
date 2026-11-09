"""A local language model for app helpers (Ollama). Always optional: apps must work without it.

    from nookkit import llm
    if llm.status()["ready"]:
        answer = llm.ask_json("Where does this go? …", schema={...}, system="You file papers.")

Settings, in ~/.config/nook/config.json (all optional):
    "llm": { "url": "http://127.0.0.1:11434", "model": "qwen2.5:3b", "timeout": 120 }
Env overrides: NOOK_LLM_URL, NOOK_LLM_MODEL.

Privacy rule: the model only ever runs on this machine. URLs that aren't loopback are refused, so a
config typo can't send someone's payslips to a server on the internet.
"""
import ipaddress
import json
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from .paths import CONFIG_ROOT

DEFAULTS = {"url": "http://127.0.0.1:11434", "model": "qwen2.5:3b", "timeout": 120}
_status_cache = {"at": 0.0, "value": None}
_lock = threading.Lock()   # one generation at a time: a CPU box can't do two at once anyway


class LLMError(Exception):
    pass


def settings():
    cfg = {}
    try:
        cfg = json.loads((CONFIG_ROOT / "config.json").read_text()).get("llm") or {}
    except (OSError, ValueError, AttributeError):
        pass
    out = {**DEFAULTS, **{k: v for k, v in cfg.items() if k in DEFAULTS and v}}
    out["url"] = os.environ.get("NOOK_LLM_URL", out["url"]).rstrip("/")
    out["model"] = os.environ.get("NOOK_LLM_MODEL", out["model"])
    return out


def is_local(url):
    u = urllib.parse.urlparse(url)
    if u.scheme not in ("http", "https") or not u.hostname:
        return False
    if u.hostname == "localhost":
        return True
    try:
        return ipaddress.ip_address(u.hostname).is_loopback
    except ValueError:
        return False


def _call(path, payload=None, timeout=5):
    s = settings()
    if not is_local(s["url"]):
        raise LLMError("The language model must run on this computer (loopback URL only)")
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(s["url"] + path, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read().decode()).get("error") or str(e)
        except ValueError:
            msg = str(e)
        raise LLMError(msg) from None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        raise LLMError(f"Can't reach the language model ({getattr(e, 'reason', e)})") from None


def status(max_age=10):
    """{"ready": bool, "running": bool, "model": str, "error": str|None}. Cached a few seconds."""
    now = time.time()
    if _status_cache["value"] and now - _status_cache["at"] < max_age:
        return _status_cache["value"]
    s = settings()
    value = {"ready": False, "running": False, "model": s["model"], "error": None}
    try:
        tags = _call("/api/tags", timeout=1.5)
        value["running"] = True
        names = {m.get("name") for m in tags.get("models", [])} | {m.get("model") for m in tags.get("models", [])}
        want = s["model"] if ":" in s["model"] else s["model"] + ":latest"
        value["ready"] = want in names
        if not value["ready"]:
            value["error"] = f"Model {s['model']} isn't downloaded (ollama pull {s['model']})"
    except LLMError as e:
        value["error"] = str(e)
    _status_cache.update(at=now, value=value)
    return value


def ask_json(prompt, schema, system="", temperature=0.1, num_ctx=4096):
    """Ask for an answer shaped like `schema` (JSON Schema). Returns the parsed dict or raises LLMError."""
    s = settings()
    messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    payload = {
        "model": s["model"], "messages": messages, "stream": False, "format": schema, "think": False,
        "keep_alive": "15m", "options": {"temperature": temperature, "num_ctx": num_ctx},
    }
    with _lock:
        out = _call("/api/chat", payload, timeout=s["timeout"])
    content = (out.get("message") or {}).get("content", "")
    try:
        answer = json.loads(content)
    except ValueError:
        raise LLMError("The model answered with something that isn't JSON") from None
    if not isinstance(answer, dict):
        raise LLMError("The model's answer has the wrong shape")
    return answer
