from __future__ import annotations

import os
import time
from collections import defaultdict, deque

from fastapi import HTTPException, status

AUTH_RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("AUTH_RATE_LIMIT_WINDOW_SECONDS", "60"))
AUTH_RATE_LIMIT_MAX_ATTEMPTS = int(os.getenv("AUTH_RATE_LIMIT_MAX_ATTEMPTS", "10"))

_attempts: dict[str, deque[float]] = defaultdict(deque)


def check_auth_rate_limit(*, action: str, key: str) -> None:
    now = time.time()
    bucket_key = f"{action}:{key.lower().strip()}"
    bucket = _attempts[bucket_key]

    while bucket and (now - bucket[0]) > AUTH_RATE_LIMIT_WINDOW_SECONDS:
        bucket.popleft()

    if len(bucket) >= AUTH_RATE_LIMIT_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many auth attempts. Please try again later.",
        )
    bucket.append(now)


def reset_auth_rate_limit_state() -> None:
    _attempts.clear()
