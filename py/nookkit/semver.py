"""Tiny semver range check, enough for app manifests ("engine": "^1.0.0")."""
import re

_V = re.compile(r"^\s*v?(\d+)\.(\d+)\.(\d+)")


def parse(v):
    m = _V.match(str(v))
    if not m:
        raise ValueError(f"not a version: {v!r}")
    return tuple(int(x) for x in m.groups())


def satisfies(version, rng):
    """Supports ^x.y.z, ~x.y.z, >=x.y.z, x.y.z and *."""
    rng = str(rng).strip()
    if rng in ("", "*"):
        return True
    v = parse(version)
    if rng.startswith("^"):
        base = parse(rng[1:])
        if base[0] > 0:
            return v[0] == base[0] and v >= base
        return v[:2] == base[:2] and v >= base
    if rng.startswith("~"):
        base = parse(rng[1:])
        return v[:2] == base[:2] and v >= base
    if rng.startswith(">="):
        return v >= parse(rng[2:])
    return v == parse(rng)
