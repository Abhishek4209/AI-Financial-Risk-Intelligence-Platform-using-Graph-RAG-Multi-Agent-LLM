"""Redis client for caching, rate limiting, and temporary state (architecture.md)."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any



@lru_cache(maxsize=1)
def get_redis_client() -> Any:
        try:
                import redis
        except ImportError as exc:
                raise RuntimeError("Install the 'redis' package to use caching") from exc
        url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        return redis.Redis.from_url(url, decode_responses=True)



def cache_get(key: str) -> Any:
        value = get_redis_client().get(key)
        return json.loads(value) if value is not None else None



def cache_set(key: str, value: Any, *, ttl_seconds: int | None = None) -> None:
        get_redis_client().set(key, json.dumps(value), ex=ttl_seconds)



def cache_delete(key: str) -> None:
        get_redis_client().delete(key)



def check_rate_limit(key: str, *, max_requests: int, window_seconds: int) -> bool:
        """Return True if the caller is within the configured request budget for this window."""
        if max_requests < 1 or window_seconds < 1:
                raise ValueError("max_requests and window_seconds must be positive")
        client = get_redis_client()
        current = client.incr(key)
        if current == 1:
                client.expire(key, window_seconds)
        return current <= max_requests
