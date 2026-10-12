"""In-memory sliding-window limiter for login attempts, keyed by IP.

Single-process default. Behind more than one API replica, point this at Redis instead
(same interface) so limits are shared — see README "Scaling beyond one replica".
"""
import time
from collections import defaultdict, deque

_hits: dict[str, deque[float]] = defaultdict(deque)


def allow(key: str, max_hits: int, window_seconds: int) -> bool:
    now = time.monotonic()
    q = _hits[key]
    while q and q[0] < now - window_seconds:
        q.popleft()
    if len(q) >= max_hits:
        return False
    q.append(now)
    return True
