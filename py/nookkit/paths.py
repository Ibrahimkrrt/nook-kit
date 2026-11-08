"""Where things live. One rule: app data goes in ~/.local/share/nook/<app-id>/ (private, 0700)."""
from pathlib import Path

HOME = Path.home()
DATA_ROOT = HOME / ".local" / "share" / "nook"
CONFIG_ROOT = HOME / ".config" / "nook"


def data_dir(app_id):
    d = DATA_ROOT / app_id
    d.mkdir(parents=True, exist_ok=True)
    d.chmod(0o700)
    return d


def user_dir(*parts, private=False):
    """A folder the user browses themselves, e.g. user_dir("Documents", "Burrow")."""
    d = HOME.joinpath(*parts)
    d.mkdir(parents=True, exist_ok=True)
    if private:
        d.chmod(0o700)
    return d
