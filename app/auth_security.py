import time
import threading


class LoginAttemptLimiter:
    """In-memory login attempt limiter with cooldown window."""

    def __init__(self, max_attempts: int, cooldown_seconds: int):
        self.max_attempts = max_attempts
        self.cooldown_seconds = cooldown_seconds
        self._attempts: dict[str, list[float]] = {}
        self._blocked_until: dict[str, float] = {}
        self._lock = threading.Lock()

    def _cleanup(self, key: str, now: float) -> None:
        window_start = now - self.cooldown_seconds
        self._attempts[key] = [ts for ts in self._attempts.get(key, []) if ts >= window_start]

    def is_blocked(self, key: str) -> bool:
        now = time.time()
        with self._lock:
            blocked_until = self._blocked_until.get(key)
            if blocked_until and blocked_until > now:
                return True
            if blocked_until and blocked_until <= now:
                self._blocked_until.pop(key, None)
            return False

    def register_failure(self, key: str) -> None:
        now = time.time()
        with self._lock:
            self._cleanup(key, now)
            self._attempts.setdefault(key, []).append(now)
            if len(self._attempts[key]) >= self.max_attempts:
                self._blocked_until[key] = now + self.cooldown_seconds
                self._attempts[key] = []

    def reset(self, key: str) -> None:
        with self._lock:
            self._attempts.pop(key, None)
            self._blocked_until.pop(key, None)
