"""
In-process token-bucket rate limiter.
No additional dependencies required — uses asyncio.Lock and a dict per key.

Applied to sensitive endpoints:
  - /auth/login        : 10 requests / 60 seconds per IP
  - /documents/upload  : 20 requests / 60 seconds per IP
"""
from __future__ import annotations

import asyncio
import time
from collections import defaultdict

_buckets: dict[str, dict] = defaultdict(lambda: {"tokens": 0.0, "last": 0.0})
_lock = asyncio.Lock()


async def check_rate_limit(key: str, limit: int, window_seconds: int = 60) -> bool:
    """
    Returns True if the request is within the rate limit, False if it should be rejected.
    Uses sliding-window token bucket logic.
    """
    now = time.monotonic()
    async with _lock:
        bucket = _buckets[key]
        elapsed = now - bucket["last"]
        bucket["last"] = now
        # Refill tokens proportional to elapsed time
        bucket["tokens"] = min(
            limit,
            bucket["tokens"] + elapsed * (limit / window_seconds),
        )
        if bucket["tokens"] >= 1.0:
            bucket["tokens"] -= 1.0
            return True
        return False
