# ai_budget.py — hard daily ceiling on DeepSeek AI calls so the API
# balance can't be drained by abuse. Date-keyed, disk-persisted and
# atomic (mirrors download_counter). When the day's limit is reached,
# the AI review is skipped and the PDF falls back to deterministic text.
#
# Max daily spend ≈ AI_DAILY_LIMIT × per-call cost (~$0.00023), so the
# loss is bounded regardless of how many IPs an attacker uses.
import json
import os
import tempfile
from datetime import date
from pathlib import Path

_DEFAULT = Path(__file__).parent / "ai_budget.json"


def _limit() -> int:
    try:
        return int(os.environ.get("AI_DAILY_LIMIT", "1000"))
    except ValueError:
        return 1000


def _path() -> Path:
    return Path(os.environ.get("AI_BUDGET_FILE", _DEFAULT))


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


def _read_today(path: Path) -> int:
    # Calls used today; 0 if missing, unreadable, or a previous day.
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("date") == date.today().isoformat():
            return int(data.get("count", 0))
    except (OSError, ValueError, TypeError):
        pass
    return 0


def _atomic_write(path: Path, count: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump({"date": date.today().isoformat(), "count": count}, fh)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def remaining() -> int:
    return max(0, _limit() - _read_today(_path()))


def try_consume(limit=None, path=None) -> bool:
    # Atomically reserve one AI call for today. True if within budget.
    # Optional limit/path override the DeepSeek defaults so another paid
    # endpoint (e.g. /api/recommend) gets an independent daily budget.
    limit = _limit() if limit is None else int(limit)
    if limit <= 0:
        return False
    path = _path() if path is None else Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix(".lock")
    with open(lock, "w") as lf:
        _lock(lf)
        try:
            used = _read_today(path)
            if used >= limit:
                return False
            _atomic_write(path, used + 1)
            return True
        finally:
            _unlock(lf)
