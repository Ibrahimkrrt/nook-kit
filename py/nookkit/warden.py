"""The model warden: loads a model in LM Studio only for as long as it's needed, and only when it fits.

Rules (the user's, and they are strict):
    1. A model is loaded on demand, used, then unloaded (after KEEP seconds without use, so a batch of papers
       doesn't reload it for every page).
    2. It runs on the graphics card only: full GPU offload, and it is loaded only when the card has room for
       it plus a margin, and the PC keeps enough free RAM. The checks use real numbers: the free memory right
       now, and what that model was measured to take last time (LM Studio's own estimate, plus a margin,
       until it has been measured).
    3. Never two models at once. If a model is already loaded (by the Nook or by the person in LM Studio),
       that one is used, if it passes the same checks, and it is left loaded afterwards (not ours to close).
       If it doesn't pass, nothing else is loaded: the app falls back to its no-AI rules.
    4. Every load gets a TTL in LM Studio too, so a crash of the Nook can't leave a model sitting in memory.

    with warden.use(server) as model_id:      # loads (or reuses) a model; raises LLMError when it can't
        call the chat API with model=model_id
"""
import atexit
import glob
import json
import re
import shutil
import subprocess
import threading
import time
from contextlib import contextmanager
from pathlib import Path

OURS = "nook"              # the identifier our loads get in LM Studio
CONTEXT = 8192             # tokens: one paper's text + instructions fit comfortably
KEEP = 20                  # seconds a model we loaded stays after its last answer
TTL = 300                  # LM Studio unloads it by itself after this (safety net)
GPU_MARGIN = 1.0           # GiB kept free on the graphics card on top of the model
RAM_RESERVE = 2.0          # GiB of RAM that must stay available to the rest of the PC
ESTIMATE_PAD = 1.25        # LM Studio's estimates run low (8B: 4.8 estimated, 5.7 real)

_lock = threading.RLock()  # one load / question / unload at a time
_timer = None
_last = {"note": None}     # what the warden did last, for the apps' status screens


class WardenError(Exception):
    pass


# ---------------------------------------------------------------- the machine
def gpu_memory():
    """(total, used) GiB of the biggest graphics card, or None when it can't be read (then nothing loads)."""
    best = None
    for f in glob.glob("/sys/class/drm/card*/device/mem_info_vram_total"):
        try:
            total = int(Path(f).read_text()) / 2**30
            used = int(Path(f.replace("_total", "_used")).read_text()) / 2**30
        except (OSError, ValueError):
            continue
        if not best or total > best[0]:
            best = (total, used)
    if best:
        return best
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.total,memory.used", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=3)
        rows = [[int(x) / 1024 for x in line.split(",")] for line in out.stdout.strip().splitlines() if out.returncode == 0]
        return max(rows) if rows else None
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def ram_available():
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) / 2**20
    except (OSError, ValueError):
        pass
    return None


def lms_cli():
    found = shutil.which("lms")
    home = Path.home() / ".lmstudio" / "bin" / "lms"
    return found or (str(home) if home.exists() else None)


# ---------------------------------------------------------------- memory book: what each model really took
def _book_path():
    from .paths import CONFIG_ROOT
    return CONFIG_ROOT / "llm-memory.json"


def _book():
    try:
        return json.loads(_book_path().read_text())
    except (OSError, ValueError):
        return {}


def _remember(key, vram, ram):
    book = _book()
    book[key] = {"vram": round(vram, 2), "ram": round(max(ram, 0), 2), "at": int(time.time())}
    p = _book_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(book, indent=2))


def _estimate(cli, key):
    """LM Studio's own estimate (GiB on the GPU, GiB in total), or None."""
    try:
        out = subprocess.run([cli, "load", key, "--estimate-only", "--gpu", "max", "-c", str(CONTEXT),
                              "--parallel", "1", "-y"], capture_output=True, text=True, timeout=60)
        out = out.stdout + out.stderr  # lms prints the estimate on stderr
    except (OSError, subprocess.SubprocessError):
        return None
    gpu = re.search(r"Estimated GPU Memory:\s*([\d.]+)\s*GiB", out)
    total = re.search(r"Estimated Total Memory:\s*([\d.]+)\s*GiB", out)
    return (float(gpu.group(1)), float(total.group(1))) if gpu and total else None


def need(key, size_gib, cli):
    """(vram, ram) GiB this model needs, from its last measurement or a padded estimate."""
    known = _book().get(key)
    if known:
        return known["vram"], known["ram"]
    est = _estimate(cli, key) if cli else None
    if est and est[1] > est[0] + 0.05:
        raise WardenError(f"{key} doesn't fit on the graphics card alone")
    vram = (est[0] if est else size_gib * 1.1) * ESTIMATE_PAD
    return vram, max(0.5, vram * 0.13)


def fits(vram_need, ram_need, gpu=None, ram=None):
    """(ok, reason). gpu = (total, used) GiB, ram = available GiB."""
    if gpu is None:
        return False, "can't read the graphics card's memory"
    free = gpu[0] - gpu[1]
    if vram_need + GPU_MARGIN > free:
        return False, f"needs {vram_need:.1f} GiB on the graphics card, {free:.1f} GiB free"
    if ram is None or ram - ram_need < RAM_RESERVE:
        return False, f"would leave less than {RAM_RESERVE:.0f} GiB of RAM for the rest of the PC"
    return True, ""


# ---------------------------------------------------------------- LM Studio
def _models(server):
    from .llm import _call
    base = server["url"][:-3] if server["url"].endswith("/v1") else server["url"]
    return _call(base, "/api/v1/models", timeout=5, token=server["token"]).get("models", [])


def loaded_llms(models):
    """[(key, instance id, size GiB)] of chat models loaded right now, whoever loaded them."""
    return [(m["key"], inst["id"], m.get("size_bytes", 0) / 2**30)
            for m in models if m.get("type") in ("llm", "vlm") for inst in m.get("loaded_instances", [])]


def _run(cli, *args, timeout=60):
    try:
        r = subprocess.run([cli, *args], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise WardenError(f"LM Studio took too long ({' '.join(args[:2])})") from None
    except OSError as e:
        raise WardenError(f"Can't run LM Studio's lms tool ({e})") from None
    if r.returncode != 0:
        raise WardenError((r.stderr or r.stdout).strip().splitlines()[-1][:200] if (r.stderr or r.stdout).strip() else "lms failed")
    return r.stdout


def _unload_ours(cli, quiet=True):
    try:
        _run(cli, "unload", OURS, timeout=30)
        _last["note"] = "unloaded"
    except WardenError:
        if not quiet:
            raise


def _schedule_unload(cli):
    global _timer
    if _timer:
        _timer.cancel()

    def later():
        with _lock:
            _unload_ours(cli)
    _timer = threading.Timer(KEEP, later)
    _timer.daemon = True
    _timer.start()


def unload_now():
    """Unload the model the Nook loaded, if any (on shutdown, and from apps' "free the GPU" buttons)."""
    global _timer
    cli = lms_cli()
    if _timer:
        _timer.cancel()
        _timer = None
    if cli:
        with _lock:
            _unload_ours(cli)


atexit.register(unload_now)


def _acquire(server, wanted):
    """Return (model id to call, ours?). wanted = [{"id", "size"}], preferred first."""
    cli = lms_cli()
    loaded = loaded_llms(_models(server))
    if loaded:
        # rule 3: someone (maybe us) already has a model loaded; use it if it is really on the graphics card
        ours = [x for x in loaded if x[1] == OURS]
        key, inst, size = (ours or loaded)[0]
        if ours:
            return inst, True
        gpu, ram = gpu_memory(), ram_available()
        if gpu is None or gpu[1] < size * 0.9:
            raise WardenError(f"{key} is loaded in LM Studio but isn't fully on the graphics card; not using it")
        if ram is None or ram < RAM_RESERVE:
            raise WardenError(f"{key} is loaded in LM Studio, but the PC is short of RAM; not using it")
        _last["note"] = f"using {key}, already loaded in LM Studio"
        return inst, False
    if not cli:
        raise WardenError("LM Studio's lms tool wasn't found, so the Nook can't load a model safely")
    reasons = []
    for m in wanted:
        try:
            vram_need, ram_need = need(m["id"], m["size"], cli)
        except WardenError as e:
            reasons.append(str(e))
            continue
        ok, why = fits(vram_need, ram_need, gpu_memory(), ram_available())
        if not ok:
            reasons.append(f"{m['id']}: {why}")
            continue
        before_gpu, before_ram = gpu_memory(), ram_available()
        _run(cli, "load", m["id"], "--gpu", "max", "-c", str(CONTEXT), "--parallel", "1",
             "--identifier", OURS, "--ttl", str(TTL), "-y", timeout=240)
        after_gpu, after_ram = gpu_memory(), ram_available()
        # check the result for real: one model only, the PC still has its RAM
        others = [x for x in loaded_llms(_models(server)) if x[1] != OURS]
        if others:
            _unload_ours(cli)
            raise WardenError(f"{others[0][0]} was loaded at the same time; unloaded ours to keep one model")
        if after_ram is None or after_ram < RAM_RESERVE - 0.5:
            _unload_ours(cli)
            raise WardenError("Loading the model left the PC short of RAM; unloaded it")
        _remember(m["id"], after_gpu[1] - before_gpu[1], before_ram - after_ram)
        _last["note"] = f"loaded {m['id']} on the graphics card ({after_gpu[1] - before_gpu[1]:.1f} GiB)"
        return OURS, True
    raise WardenError("No model fits right now (" + "; ".join(reasons) + ")")


@contextmanager
def use(server, wanted):
    """Hold a model for one question. `wanted`: [{"id", "size"}] in order of preference."""
    with _lock:
        global _timer
        if _timer:
            _timer.cancel()
            _timer = None
        model, ours = _acquire(server, wanted)
        try:
            yield model
        finally:
            if ours:
                _schedule_unload(lms_cli())


def note():
    return _last["note"]
