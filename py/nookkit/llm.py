"""A local language model for app helpers. Always optional: apps must work without it.

    from nookkit import llm
    if llm.status()["ready"]:
        answer = llm.ask_json("Where does this go? …", schema={...}, system="You file papers.")

Works with the models already on this computer, whichever server holds them:
    - LM Studio (http://127.0.0.1:1234/v1, OpenAI-style API, usually with an API token)
    - llama.cpp's llama-server (http://127.0.0.1:8080/v1)
    - Ollama (http://127.0.0.1:11434)
With nothing configured it looks for a running one, in that order, and picks a model it already has
(the smallest proper chat model: on a PC without a big GPU, that's the one that answers in seconds).

Settings, all optional, later wins:
    ~/.config/nook/config.json  "llm": { "url": "…", "model": "…", "timeout": 120 }
    ~/.config/nook/llm.json     written by save() (the model picked in an app, the server's API token); 0600
    env NOOK_LLM_URL, NOOK_LLM_MODEL
A URL ending in /v1 is spoken to as an OpenAI-style server, anything else as Ollama ("api" overrides).

Privacy rule: the model only ever runs on this machine. URLs that aren't loopback are refused, so a
config typo can't send someone's payslips to a server on the internet.
"""
import ipaddress
import json
import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from . import warden
from .paths import CONFIG_ROOT

SERVERS = [  # looked for in this order when no URL is configured
    ("LM Studio", "openai", "http://127.0.0.1:1234/v1"),
    ("llama.cpp", "openai", "http://127.0.0.1:8080/v1"),
    ("Ollama", "ollama", "http://127.0.0.1:11434"),
]
DEFAULTS = {"url": "", "model": "", "timeout": 120, "api": "auto"}
SAVED = CONFIG_ROOT / "llm.json"
_status_cache = {"at": 0.0, "value": None, "pick": None}
_lock = threading.Lock()   # one generation at a time: a CPU box can't do two at once anyway


class LLMError(Exception):
    pass


class _NeedsToken(LLMError):
    pass


def _read(path):
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def settings():
    """The merged settings, token included (never send this to a browser)."""
    cfg = _read(CONFIG_ROOT / "config.json").get("llm") or {}
    saved = _read(SAVED)
    out = {**DEFAULTS, "token": ""}
    for src in (cfg, saved):
        out.update({k: v for k, v in src.items() if k in (*DEFAULTS, "token") and v})
    out["url"] = os.environ.get("NOOK_LLM_URL", out["url"]).rstrip("/")
    out["model"] = os.environ.get("NOOK_LLM_MODEL", out["model"])
    return out


def save(**changes):
    """Remember the model picked in an app and/or the server's API token. Pass "" to forget one."""
    data = _read(SAVED)
    for k, v in changes.items():
        if k not in ("model", "token", "url"):
            raise ValueError(k)
        if v:
            data[k] = v
        else:
            data.pop(k, None)
    CONFIG_ROOT.mkdir(parents=True, exist_ok=True)
    tmp = SAVED.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, SAVED)
    _status_cache.update(at=0.0, value=None, pick=None)


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


def _api_for(url, api="auto"):
    if api in ("openai", "ollama"):
        return api
    return "openai" if urllib.parse.urlparse(url).path.rstrip("/").endswith("/v1") else "ollama"


def _name_for(url, api):
    for name, a, u in SERVERS:
        if a == api and urllib.parse.urlparse(u).port == urllib.parse.urlparse(url).port:
            return name
    return "Ollama" if api == "ollama" else "Local server"


def _call(url, path, payload=None, timeout=5, token=""):
    if not is_local(url):
        raise LLMError("The language model must run on this computer (loopback URL only)")
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url + path, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            err = json.loads(raw).get("error") or raw
            msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
        except (ValueError, AttributeError):
            msg = raw or str(e)
        if e.code in (401, 403):
            raise _NeedsToken(msg[:300]) from None
        raise LLMError(msg[:300]) from None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        raise LLMError(f"Can't reach the language model ({getattr(e, 'reason', e)})") from None


# ---------------------------------------------------------------- what's installed
_SIZE = re.compile(r"(?<![\d.])(\d+(?:\.\d+)?)\s*b(?![a-z])")


def _params(*texts):
    """Billions of parameters, from "8.0B" or a name like "qwen3-8b" (None if unknown)."""
    for t in texts:
        m = _SIZE.search(str(t or "").lower())
        if m:
            return float(m.group(1))
    return None


def _models(url, api, token, timeout=1.5):
    """[{"id", "params", "chat"}] for one server. Raises LLMError when it isn't there."""
    out = []
    if api == "ollama":
        for m in _call(url, "/api/tags", timeout=timeout).get("models", []):
            d = m.get("details") or {}
            name = m.get("name") or m.get("model")
            embed = "bert" in str(d.get("family", "")).lower() or "embed" in name.lower()
            out.append({"id": name, "params": _params(d.get("parameter_size"), name), "chat": not embed})
        return out
    base = url[:-3] if url.endswith("/v1") else url
    try:  # LM Studio's newer listing: types, file sizes, what's loaded (the warden needs all three)
        rows = _call(base, "/api/v1/models", timeout=timeout, token=token).get("models", [])
        for m in rows:
            out.append({"id": m["key"], "params": _params(m.get("params_string"), m["key"]),
                        "chat": m.get("type") in ("llm", "vlm"), "size": m.get("size_bytes", 0) / 2**30,
                        "loaded": bool(m.get("loaded_instances")), "managed": True})
        return out
    except _NeedsToken:
        raise
    except (LLMError, KeyError, TypeError):
        out = []
    try:  # LM Studio's older listing says which ones are embedding models
        rows = _call(base, "/api/v0/models", timeout=timeout, token=token).get("data", [])
        for m in rows:
            out.append({"id": m["id"], "params": _params(m["id"]), "chat": m.get("type") in ("llm", "vlm")})
        return out
    except _NeedsToken:
        raise
    except LLMError:
        pass
    for m in _call(url, "/models", timeout=timeout, token=token).get("data", []):
        out.append({"id": m["id"], "params": _params(m["id"]), "chat": "embed" not in m["id"].lower()})
    return out


def _auto_model(models):
    """The smallest real chat model (>= 3B when sizes are known): quick enough on a CPU, good enough to file."""
    chat = [m for m in models if m["chat"]]
    if not chat:
        return ""
    sized = sorted((m for m in chat if m["params"]), key=lambda m: m["params"])
    good = [m for m in sized if m["params"] >= 3] or sized
    return (good[0] if good else chat[0])["id"]


def status(max_age=10):
    """What the apps show: {"ready", "running", "server", "model", "picked": "you"|"auto", "models": [...],
    "needs_token", "error"}. Never contains the token. Cached a few seconds."""
    now = time.time()
    if _status_cache["value"] and now - _status_cache["at"] < max_age:
        return _status_cache["value"]
    s = settings()
    tries = [(_name_for(s["url"], _api_for(s["url"], s["api"])), _api_for(s["url"], s["api"]), s["url"])] if s["url"] else SERVERS
    value = {"ready": False, "running": False, "server": None, "model": None, "picked": None,
             "models": [], "needs_token": False, "error": None}
    ram = _ram_gb()
    pick = None
    for name, api, url in tries:
        try:
            models = _models(url, api, s["token"])
        except _NeedsToken as e:
            if not value["running"]:
                value.update(running=True, server=name, needs_token=True,
                             error=f"{name} is running but asks for an API token" if not s["token"] else f"{name} refused the API token ({e})")
            continue
        except LLMError as e:
            value["error"] = value["error"] or str(e)
            continue
        chat = [m for m in models if m["chat"]]
        if not chat:  # running, but nothing to talk to: try the next server before saying so
            if not value["running"]:
                value.update(running=True, server=name, error=f"{name} is running but has no chat models")
            continue
        ids = {m["id"] for m in chat}
        if api == "ollama":  # "qwen3" means "qwen3:latest"
            ids |= {i.removesuffix(":latest") for i in ids}
        chosen = s["model"] if s["model"] in ids else _auto_model(models)
        book = warden._book()
        managed = any(m.get("managed") for m in models)
        loaded = [m["id"] for m in chat if m.get("loaded")]
        value = {"ready": True, "running": True, "server": name, "model": chosen,
                 "picked": "you" if chosen == s["model"] else "auto",
                 "models": [{"id": m["id"], "params": m["params"], "size_gb": round(m.get("size", 0), 1) or None,
                             "need_gb": (book.get(m["id"]) or {}).get("vram")} for m in chat],
                 "needs_token": False, "error": None,
                 # LM Studio: the warden loads a model only when needed, GPU only, one at a time
                 "on_demand": managed, "loaded": loaded, "keep_seconds": warden.KEEP if managed else None,
                 "warden": warden.note() if managed else None}
        if s["model"] and s["model"] not in ids:
            value["error"] = f"{s['model']} isn't on {name}; using {chosen}"
        order = [m for m in chat if m["id"] == chosen] + sorted(
            (m for m in chat if m["id"] != chosen), key=lambda m: m.get("size") or (m["params"] or 99))
        pick = {"api": api, "url": url, "model": chosen, "token": s["token"], "timeout": s["timeout"], "name": name,
                "managed": managed, "wanted": [{"id": m["id"], "size": m.get("size") or 0} for m in order]}
        break
    value["ram_gb"] = ram  # so apps can say which models fit the graphics card, and which are too big
    value["vram_gb"] = _vram_gb()
    _status_cache.update(at=now, value=value, pick=pick)
    return value


def _ram_gb():
    try:
        return round(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2**30, 1)
    except (ValueError, OSError, AttributeError):
        return None


def _vram_gb():
    """The biggest graphics card's memory (AMD via sysfs, NVIDIA via nvidia-smi), or None."""
    import glob
    import subprocess
    sizes = []
    for f in glob.glob("/sys/class/drm/card*/device/mem_info_vram_total"):
        try:
            sizes.append(int(open(f).read()) / 2**30)
        except (OSError, ValueError):
            pass
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=2)
        sizes += [int(x) / 1024 for x in out.stdout.split() if x.isdigit()] if out.returncode == 0 else []
    except (OSError, subprocess.SubprocessError):
        pass
    return round(max(sizes), 1) if sizes else None


def _strip_think(text):
    return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()


def ask_json(prompt, schema, system="", temperature=0.1, num_ctx=4096):
    """Ask for an answer shaped like `schema` (JSON Schema). Returns the parsed dict or raises LLMError."""
    status(max_age=30)
    p = _status_cache["pick"]
    if not p:
        raise LLMError(_status_cache["value"]["error"] or "No local language model is available")
    model = p["model"]
    if "qwen3" in model.lower():
        prompt += "\n/no_think"  # Qwen3's switch: answer straight away instead of thinking out loud first
    messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    if p.get("managed"):  # LM Studio: load on demand onto the graphics card, one model at a time
        try:
            with _lock, warden.use(p, p["wanted"]) as instance:
                out = _call(p["url"], "/chat/completions", {
                    "model": instance, "messages": messages, "stream": False, "temperature": temperature,
                    "max_tokens": 1024,
                    "response_format": {"type": "json_schema", "json_schema": {"name": "answer", "strict": True, "schema": schema}},
                }, timeout=p["timeout"], token=p["token"])
        except warden.WardenError as e:
            raise LLMError(str(e)) from None
        finally:
            _status_cache["at"] = 0.0  # what's loaded changed
        content = ((out.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
        return _parse(content)
    with _lock:
        if p["api"] == "ollama":
            out = _call(p["url"], "/api/chat", {
                "model": model, "messages": messages, "stream": False, "format": schema, "think": False,
                "keep_alive": f"{warden.KEEP}s", "options": {"temperature": temperature, "num_ctx": num_ctx},
            }, timeout=p["timeout"])
            content = (out.get("message") or {}).get("content", "")
        else:
            out = _call(p["url"], "/chat/completions", {
                "model": model, "messages": messages, "stream": False, "temperature": temperature,
                "max_tokens": 1024,
                "response_format": {"type": "json_schema", "json_schema": {"name": "answer", "strict": True, "schema": schema}},
            }, timeout=p["timeout"], token=p["token"])
            content = ((out.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    return _parse(content)


def _parse(content):
    try:
        answer = json.loads(_strip_think(content))
    except ValueError:
        raise LLMError("The model answered with something that isn't JSON") from None
    if not isinstance(answer, dict):
        raise LLMError("The model's answer has the wrong shape")
    return answer
