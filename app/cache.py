"""In-memory caching utilities for CarbonCompass.

This module provides a simple in-memory cache system with time-to-live (TTL)
expiration support and integration with application usage statistics.
"""

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from app.state import increment_stat

logger = logging.getLogger("carboncompass")


@dataclass
class CacheEntry:
    """A single cache entry record.

    Attributes:
        value (Any): Cached payload data.
        timestamp (float): Ephemeral timestamp (Unix epoch seconds) when cache was set.
        ttl (int): Lifetime duration of this entry in seconds.
    """

    value: Any
    timestamp: float
    ttl: int


class SimpleCache:
    """An in-memory dictionary-backed cache with simple eviction logic."""

    def __init__(self) -> None:
        """Initialize the cache dictionary store."""
        self._store: Dict[str, CacheEntry] = {}

    def get(self, key: str) -> Optional[Any]:
        """Retrieve a cached value if it exists and has not expired.

        Args:
            key (str): Lookup key identifier.

        Returns:
            Optional[Any]: The cached value if fresh, or None on miss/expiry.
        """
        entry = self._store.get(key)
        if entry:
            if time.time() - entry.timestamp < entry.ttl:
                increment_stat("cache_hits")
                logger.info(
                    "cache_hit",
                    extra={
                        "endpoint": f"/api/v1/{key}",
                        "request_id": "cache",
                        "cache_key": key,
                    },
                )
                return entry.value
            self.invalidate(key)

        logger.info(
            "cache_miss",
            extra={
                "endpoint": f"/api/v1/{key}",
                "request_id": "cache",
                "cache_key": key,
            },
        )
        return None

    def set(self, key: str, value: Any, ttl: int) -> None:
        """Store a value in the cache with a specified time-to-live.

        Args:
            key (str): Lookup key identifier.
            value (Any): The payload to cache.
            ttl (int): Time-to-live duration in seconds.
        """
        self._store[key] = CacheEntry(value=value, timestamp=time.time(), ttl=ttl)

    def invalidate(self, key: str) -> None:
        """Explicitly evict an item from the cache.

        Args:
            key (str): The key to remove.
        """
        if key in self._store:
            del self._store[key]

    def clear(self) -> None:
        """Wipe the entire cache store."""
        self._store.clear()


# Cache singleton instance
cache = SimpleCache()


def get_cached(key: str) -> Optional[Any]:
    """Retrieve an item from the singleton cache instance.

    Args:
        key (str): Cache lookup key.

    Returns:
        Optional[Any]: The cached payload, or None if expired/not found.
    """
    return cache.get(key)


def set_cached(key: str, value: Any, ttl: int) -> None:
    """Store an item in the singleton cache instance.

    Args:
        key (str): Cache lookup key.
        value (Any): Payload to cache.
        ttl (int): Duration in seconds to retain the item.
    """
    cache.set(key, value, ttl)


# Backward compatibility wrappers
def get_cached_response(cache_key: str) -> Optional[Any]:
    """Compatibility wrapper for get_cached.

    Args:
        cache_key (str): Cache lookup key.

    Returns:
        Optional[Any]: The cached payload.
    """
    return get_cached(cache_key)


def set_cached_response(cache_key: str, data: Any) -> None:
    """Compatibility wrapper for set_cached.

    Args:
        cache_key (str): Cache lookup key.
        data (Any): Payload to cache.
    """
    from app.constants import CACHE_TTL_SECONDS

    cache.set(cache_key, data, CACHE_TTL_SECONDS)
