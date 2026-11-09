"""Safe file uploads. The hub only accepts JSON, so files arrive base64-encoded.

    data, ext = decode_upload(req.body.get("data"), req.str("filename"), DOCUMENTS)
    path = unique_path(folder, f"{period} - {safe_name(stem)}{ext}")
"""
import base64
import re
import unicodedata
from pathlib import Path

MB = 1024 * 1024

# extension -> (mime type, magic bytes check)
DOCUMENTS = {
    ".pdf": ("application/pdf", lambda b: b.startswith(b"%PDF")),
    ".png": ("image/png", lambda b: b.startswith(b"\x89PNG\r\n\x1a\n")),
    ".jpg": ("image/jpeg", lambda b: b.startswith(b"\xff\xd8\xff")),
    ".jpeg": ("image/jpeg", lambda b: b.startswith(b"\xff\xd8\xff")),
    ".webp": ("image/webp", lambda b: b[:4] == b"RIFF" and b[8:12] == b"WEBP"),
}


class UploadError(ValueError):
    """Message is safe to show to the user."""


def decode_upload(b64, filename, allowed=DOCUMENTS, max_bytes=20 * MB):
    """Returns (bytes, ext). Raises UploadError with a friendly message."""
    ext = Path(filename or "").suffix.lower()
    if ext not in allowed:
        kinds = ", ".join(sorted({e.lstrip(".").upper() for e in allowed}))
        raise UploadError(f"Only {kinds} files")
    if not isinstance(b64, str) or len(b64) > (max_bytes * 4) // 3 + 16:
        raise UploadError(f"Too big: max {max_bytes // MB} MB")
    try:
        data = base64.b64decode(b64, validate=True)
    except ValueError:
        raise UploadError("The file didn't arrive in one piece") from None
    if not data:
        raise UploadError("That file is empty")
    if len(data) > max_bytes:
        raise UploadError(f"Too big: max {max_bytes // MB} MB")
    _, looks_right = allowed[ext]
    if not looks_right(data):
        raise UploadError(f"That isn't really a {ext.lstrip('.').upper()} file")
    return data, ext


def mime_for(path, allowed=DOCUMENTS):
    return allowed.get(Path(path).suffix.lower(), ("application/octet-stream",))[0]


def safe_name(name, max_len=80):
    """'Fiche de paie – Février 2025' → 'Fiche de paie - Fevrier 2025' (ASCII, no path tricks)."""
    name = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode()
    name = re.sub(r"[^A-Za-z0-9._ -]+", "_", name)
    name = re.sub(r"\s+", " ", name).strip(" ._") or "file"
    return name[:max_len]


def unique_path(folder, filename):
    """folder/filename, or folder/filename (2), (3)… if it exists."""
    folder = Path(folder)
    target = folder / filename
    stem, ext = target.stem, target.suffix
    n = 2
    while target.exists():
        target = folder / f"{stem} ({n}){ext}"
        n += 1
    return target


def inside(path, folder):
    """True if path really is inside folder (after resolving symlinks and ..)."""
    try:
        return Path(folder).resolve() in Path(path).resolve().parents
    except OSError:
        return False


def extract_text(path, max_chars=6000, pages=3):
    """Readable text from a document, for search or a language model. "" when there's none.

    PDFs go through poppler's pdftotext (first few pages); images through tesseract when it's
    installed (eng+fra). Never raises: a document we can't read just has no text.
    """
    import shutil
    import subprocess

    path = Path(path)
    ext = path.suffix.lower()
    try:
        if ext == ".pdf" and shutil.which("pdftotext"):
            out = subprocess.run(["pdftotext", "-q", "-layout", "-l", str(pages), "-enc", "UTF-8", str(path), "-"],
                                 capture_output=True, timeout=20).stdout
        elif ext in (".png", ".jpg", ".jpeg", ".webp") and shutil.which("tesseract"):
            out = subprocess.run(["tesseract", str(path), "-", "-l", "eng+fra"], capture_output=True, timeout=40).stdout
        else:
            return ""
    except (OSError, subprocess.SubprocessError):
        return ""
    text = out.decode("utf-8", "replace")
    text = re.sub(r"[ \t]{2,}", "  ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()[:max_chars]
