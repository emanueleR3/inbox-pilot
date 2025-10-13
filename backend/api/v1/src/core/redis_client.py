from functools import lru_cache
from typing import Optional

import redis

from src.core.config import settings


@lru_cache(maxsize=1)
def get_redis_client() -> redis.Redis:
    """Return a singleton Redis client using URL from settings.

    Uses connection pooling under the hood. If REDIS_URL is invalid
    or Redis is unreachable at runtime, callers should handle exceptions.
    """
    return redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,  # store/read strings directly
        password=settings.REDIS_PASSWORD,  # Add password if your Redis instance requires it
    )
