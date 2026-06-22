# rate_limit.py — tiny in-process sliding-window limiter (per key).
# Defense-in-depth in front of the AI export route: caps how fast one
# IP can spend the daily budget and blunts bursty abuse / DoS.
#
# In-process only: with multiple workers the effective limit is
# per-worker. The cross-process spend ceiling is ai_budget; this is a
# UX/DoS smoother, not the balance guarantee.
import time
from collections import defaultdict, deque

_hits = defaultdict(deque)
_MAX_KEYS = 10000          # bound memory against IP-spraying


def allow(key: str, limit: int, window_s: float) -> bool:
    # True if `key` has made < limit hits in the last window_s seconds.
    now = time.time()
    dq = _hits[key]
    cutoff = now - window_s
    while dq and dq[0] <= cutoff:
        dq.popleft()
    if not dq and len(_hits) > _MAX_KEYS:
        _hits.pop(key, None)        # drop the just-created empty entry
        _gc(cutoff)
    if len(dq) >= limit:
        return False
    dq.append(now)
    return True


def _gc(cutoff: float) -> None:
    # Evict keys whose most recent hit is older than the window.
    stale = [k for k, d in _hits.items() if not d or d[-1] <= cutoff]
    for k in stale:
        _hits.pop(k, None)
