from __future__ import annotations

import math
import threading
import time
from collections import deque

MAX_TRACKED_KEYS = 10_000


class SlidingWindowRateLimiter:
    """Thread-safe in-memory rate limiter with per-key sliding windows."""

    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def allow(self, *, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        now = time.time()
        cutoff = now - float(window_seconds)

        with self._lock:
            if len(self._events) >= MAX_TRACKED_KEYS:
                self._evict_expired(cutoff)
            bucket = self._events.setdefault(key, deque())
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()

            if len(bucket) >= limit:
                oldest = bucket[0]
                retry_after = max(1, int(math.ceil((oldest + window_seconds) - now)))
                return False, retry_after

            bucket.append(now)
            return True, 0

    def _evict_expired(self, cutoff: float) -> None:
        expired = [key for key, bucket in self._events.items() if not bucket or bucket[-1] <= cutoff]
        for key in expired:
            del self._events[key]
