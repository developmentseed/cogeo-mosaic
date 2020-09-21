"""backend cache configuration"""
import functools
import os
from typing import Callable

from cachetools import TTLCache, cached

# TTL of the cache in seconds
COGEO_MOSAIC_CACHE_TTL = int(os.getenv("CACHE_TTL", 300))

# Maximum size of the LRU cache in MB
COGEO_MOSAIC_CACHE_MAXSIZE = int(os.getenv("CACHE_MAXSIZE", 512))

# Whether or not caching is enabled
COGEO_MOSAIC_CACHE_ENABLED = os.getenv("CACHE_ENABLED", "TRUE")


def lru_cache(key: Callable) -> Callable:
    """Decorator to optionally cache the result of an instance method"""

    def decorator(func: Callable) -> Callable:
        if COGEO_MOSAIC_CACHE_ENABLED == "TRUE":

            def wrapper(*args, **kwargs):
                cache_deco = cached(
                    TTLCache(
                        maxsize=COGEO_MOSAIC_CACHE_MAXSIZE, ttl=COGEO_MOSAIC_CACHE_TTL
                    ),
                    key=key,
                )
                return cache_deco(func)(*args, **kwargs)

        else:

            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

        return functools.update_wrapper(wrapper, func)

    return decorator
