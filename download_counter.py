# download_counter.py — tiny disk-persisted counter for .docx exports.
# Survives restarts so a live deploy keeps a running download total.
# Storage path is overridable via DOWNLOAD_COUNT_FILE (tests/deploys).
import json
import os
import tempfile
from pathlib import Path

_DEFAULT = Path(__file__).parent / "download_count.json"

# Advisory file lock on POSIX so concurrent workers don't clobber the
# count; no-op fallback where fcntl is unavailable (e.g. Windows).
try:
    import fcntl

    def _lock(fh):
        fcntl.flock(fh, fcntl.LOCK_EX)

    def _unlock(fh):
        fcntl.flock(fh, fcntl.LOCK_UN)
except ImportError:  # pragma: no cover - platform dependent
    def _lock(fh):
        pass

    def _unlock(fh):
        pass


def _path() -> Path:
    return Path(os.environ.get("DOWNLOAD_COUNT_FILE", _DEFAULT))


def read_count() -> int:
    # Current total; 0 if the file is missing or unreadable.
    try:
        data = json.loads(_path().read_text(encoding="utf-8"))
        return int(data.get("count", 0))
    except (OSError, ValueError, TypeError):
        return 0


def _atomic_write(path: Path, count: int) -> None:
    # Write to a temp file in the same dir, then replace — never
    # leaves a half-written count if the process dies mid-write.
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump({"count": count}, fh)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def increment() -> int:
    # Atomically bump the counter and return the new total.
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix(".lock")
    with open(lock, "w") as lf:
        _lock(lf)
        try:
            count = read_count() + 1
            _atomic_write(path, count)
            return count
        finally:
            _unlock(lf)
