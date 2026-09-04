from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import hashlib
import os
import stat

MAX_FILE_BYTES = 64 * 1024 * 1024
_READ_CHUNK = 1024 * 1024

@dataclass(frozen=True)
class FileFingerprint:
    path: str
    status: str
    sha256: str | None = None
    size: int | None = None
    resolved_path: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _inside(root: Path, target: Path) -> bool:
    try:
        target.relative_to(root)
        return True
    except ValueError:
        return False


def fingerprint(path: str | os.PathLike[str], workspace: str | os.PathLike[str]) -> FileFingerprint:
    raw_path = str(path)
    try:
        root = Path(workspace).resolve(strict=True)
    except (OSError, RuntimeError):
        return FileFingerprint(raw_path, "OUTSIDE_SCOPE")
    if not root.is_dir():
        return FileFingerprint(raw_path, "OUTSIDE_SCOPE")

    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = root / candidate
    try:
        resolved = candidate.resolve(strict=False)
    except (OSError, RuntimeError):
        return FileFingerprint(raw_path, "UNREADABLE")
    if not _inside(root, resolved):
        return FileFingerprint(raw_path, "OUTSIDE_SCOPE", resolved_path=str(resolved))
    try:
        lst = candidate.lstat()
    except FileNotFoundError:
        return FileFingerprint(raw_path, "MISSING", resolved_path=str(resolved))
    except OSError:
        return FileFingerprint(raw_path, "UNREADABLE", resolved_path=str(resolved))

    try:
        st = candidate.stat()
    except FileNotFoundError:
        return FileFingerprint(raw_path, "MISSING", resolved_path=str(resolved))
    except OSError:
        return FileFingerprint(raw_path, "UNREADABLE", resolved_path=str(resolved))
    if not stat.S_ISREG(st.st_mode):
        return FileFingerprint(raw_path, "NON_REGULAR", resolved_path=str(resolved))
    if st.st_size > MAX_FILE_BYTES:
        return FileFingerprint(raw_path, "TOO_LARGE", size=st.st_size, resolved_path=str(resolved))
    # Treat no-readable-bit files as unreadable even when tests execute as root.
    if st.st_mode & 0o444 == 0:
        return FileFingerprint(raw_path, "UNREADABLE", size=st.st_size, resolved_path=str(resolved))

    fd = None
    try:
        fd = os.open(candidate, os.O_RDONLY)
        pre = os.fstat(fd)
        if not stat.S_ISREG(pre.st_mode):
            return FileFingerprint(raw_path, "NON_REGULAR", resolved_path=str(resolved))
        if pre.st_size > MAX_FILE_BYTES:
            return FileFingerprint(raw_path, "TOO_LARGE", size=pre.st_size, resolved_path=str(resolved))
        h = hashlib.sha256()
        total = 0
        while True:
            block = os.read(fd, _READ_CHUNK)
            if not block:
                break
            total += len(block)
            if total > MAX_FILE_BYTES:
                return FileFingerprint(raw_path, "TOO_LARGE", size=total, resolved_path=str(resolved))
            h.update(block)
        post = os.fstat(fd)
    except FileNotFoundError:
        return FileFingerprint(raw_path, "MISSING", resolved_path=str(resolved))
    except OSError:
        return FileFingerprint(raw_path, "UNREADABLE", resolved_path=str(resolved))
    finally:
        if fd is not None:
            os.close(fd)

    stable_fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
    if any(getattr(pre, f) != getattr(post, f) for f in stable_fields):
        return FileFingerprint(raw_path, "UNSTABLE", size=post.st_size, resolved_path=str(resolved))
    return FileFingerprint(raw_path, "OK", h.hexdigest(), post.st_size, str(resolved))


def compare_fingerprint(previous: dict, current: FileFingerprint) -> str:
    """Return FRESH, STALE, or UNKNOWN. Fail closed for current-state evidence."""
    if previous.get("status") != "OK" or current.status != "OK":
        return "UNKNOWN"
    keys = ("sha256", "size", "resolved_path")
    return "FRESH" if all(previous.get(k) == getattr(current, k) for k in keys) else "STALE"
