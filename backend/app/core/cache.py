"""
Analytica — Caching Layer
Redis-backed cache with an in-process TTLCache fallback.

The public API (get_cache / set_cache / clear_cache / make_cache_key) is
unchanged, so existing call sites keep working. When REDIS_URL is set and
reachable, keys are stored in Redis (namespaced under ``analytica:``);
otherwise the process-local TTLCache is used.
"""

import json
import os
from typing import Any, Optional

from cachetools import TTLCache

try:
    from redis import Redis
except ImportError:  # redis not installed -> in-memory cache only
    Redis = None

_MEMORY_PREFIX = "analytica:"

_memory: TTLCache | None = None
_redis: Optional[Redis] = None
_redis_unavailable: bool = False


def _get_memory() -> TTLCache:
    global _memory
    if _memory is None:
        maxsize = int(os.getenv("CACHE_MAXSIZE", "500"))
        ttl = int(os.getenv("CACHE_TTL", "60"))
        _memory = TTLCache(maxsize=maxsize, ttl=ttl)
    return _memory


def _get_redis() -> Optional[Redis]:
    """Lazily build and probe the Redis client; disable it permanently on failure."""
    global _redis, _redis_unavailable
    if Redis is None or _redis is not None or _redis_unavailable:
        return _redis
    url = os.getenv("REDIS_URL", "")
    if not url:
        _redis_unavailable = True
        return None
    try:
        client = Redis.from_url(
            url,
            socket_connect_timeout=1.0,
            socket_timeout=1.0,
            decode_responses=False,
        )
        client.ping()
    except Exception:
        _redis_unavailable = True
        return None
    _redis = client
    return _redis


def _encode(value: Any) -> bytes:
    return json.dumps(value, default=str).encode("utf-8")


def _decode(raw: bytes | None) -> Optional[Any]:
    if raw is None:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return raw


def _default_ttl() -> int:
    return int(os.getenv("CACHE_TTL", "60"))


def get_cache(key: str) -> Optional[Any]:
    redis = _get_redis()
    if redis is not None:
        try:
            return _decode(redis.get(_MEMORY_PREFIX + key))
        except Exception:
            pass
    return _get_memory().get(key)


def set_cache(key: str, value: Any, ttl_seconds: int | None = None) -> None:
    redis = _get_redis()
    ttl = ttl_seconds if ttl_seconds is not None else _default_ttl()
    if redis is not None:
        try:
            redis.set(_MEMORY_PREFIX + key, _encode(value), ex=ttl)
            return
        except Exception:
            pass
    _get_memory()[key] = value


def clear_cache() -> None:
    redis = _get_redis()
    if redis is not None:
        try:
            cursor = 0
            while True:
                cursor, keys = redis.scan(cursor, match=_MEMORY_PREFIX + "*", count=500)
                if keys:
                    redis.delete(*keys)
                if cursor == 0:
                    break
        except Exception:
            pass
    _get_memory().clear()


def make_cache_key(prefix: str, filters: dict) -> str:
    filter_str = "&".join(
        f"{k}={v}" for k, v in sorted(filters.items())
        if v is not None and str(v).strip().lower() not in ("all", "all_time", "none", "null", "")
    )
    return f"{prefix}:{filter_str}" if filter_str else prefix
