"""
Simple response caching utilities for FastAPI endpoints.
Provides in-memory caching with TTL support.
"""

import asyncio
import functools
import hashlib
import json
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class CacheEntry:
    """Represents a cached value with expiration."""
    
    def __init__(self, value: Any, expires_at: datetime):
        self.value = value
        self.expires_at = expires_at
        self.hits = 0
    
    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        return datetime.now(timezone.utc) >= self.expires_at
    
    def get_value(self) -> Any:
        """Get the cached value and increment hit counter."""
        self.hits += 1
        return self.value


class SimpleCache:
    """
    Simple in-memory cache with TTL support.
    
    Thread-safe cache implementation for FastAPI endpoints.
    Uses LRU eviction when max size is reached.
    """
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        """
        Initialize cache.
        
        Args:
            max_size: Maximum number of entries to store
            default_ttl: Default time-to-live in seconds
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._lock = asyncio.Lock()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expirations': 0
        }
    
    def _generate_key(self, *args: Any, **kwargs: Any) -> str:
        """Generate cache key from arguments."""
        key_data = {
            'args': args,
            'kwargs': sorted(kwargs.items())
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        async with self._lock:
            if key not in self._cache:
                self._stats['misses'] += 1
                return None
            
            entry = self._cache[key]
            
            if entry.is_expired():
                del self._cache[key]
                self._stats['expirations'] += 1
                self._stats['misses'] += 1
                return None
            
            self._stats['hits'] += 1
            return entry.get_value()
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if not specified)
        """
        async with self._lock:
            # Evict if at max size
            if len(self._cache) >= self._max_size and key not in self._cache:
                await self._evict_oldest()
            
            expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=ttl or self._default_ttl
            )
            self._cache[key] = CacheEntry(value, expires_at)
    
    async def _evict_oldest(self) -> None:
        """Evict the oldest entry from cache."""
        if not self._cache:
            return
        
        # Find entry with earliest expiration
        oldest_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].expires_at
        )
        
        del self._cache[oldest_key]
        self._stats['evictions'] += 1
        logger.debug(f"Evicted cache entry: {oldest_key[:8]}...")
    
    async def delete(self, key: str) -> None:
        """Delete entry from cache."""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
    
    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()
            logger.info("Cache cleared")
    
    async def cleanup_expired(self) -> int:
        """
        Remove all expired entries.
        
        Returns:
            Number of entries removed
        """
        async with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                del self._cache[key]
            
            if expired_keys:
                self._stats['expirations'] += len(expired_keys)
                logger.debug(f"Cleaned up {len(expired_keys)} expired entries")
            
            return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._stats['hits'] + self._stats['misses']
        hit_rate = (
            self._stats['hits'] / total_requests * 100
            if total_requests > 0
            else 0
        )
        
        return {
            'size': len(self._cache),
            'max_size': self._max_size,
            'hits': self._stats['hits'],
            'misses': self._stats['misses'],
            'hit_rate': f"{hit_rate:.2f}%",
            'evictions': self._stats['evictions'],
            'expirations': self._stats['expirations']
        }


# Global cache instance
_global_cache: Optional[SimpleCache] = None


def get_cache() -> SimpleCache:
    """Get or create the global cache instance."""
    global _global_cache
    if _global_cache is None:
        _global_cache = SimpleCache(max_size=1000, default_ttl=300)
    return _global_cache


def cached(ttl: int = 300, key_prefix: str = ""):
    """
    Decorator to cache function results.
    
    Args:
        ttl: Time-to-live in seconds
        key_prefix: Optional prefix for cache keys
        
    Example:
        @cached(ttl=60)
        async def get_expensive_data():
            return await compute_something()
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            cache = get_cache()
            
            # Generate cache key
            cache_key_data = f"{key_prefix}:{func.__name__}:{args}:{kwargs}"
            cache_key = hashlib.md5(cache_key_data.encode()).hexdigest()
            
            # Try to get from cache
            cached_value = await cache.get(cache_key)
            if cached_value is not None:
                logger.debug(
                    f"Cache hit: {func.__name__} (key: {cache_key[:8]}...)"
                )
                return cached_value
            
            # Compute value
            logger.debug(
                f"Cache miss: {func.__name__} (key: {cache_key[:8]}...)"
            )
            result = await func(*args, **kwargs)
            
            # Store in cache
            await cache.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator


async def cache_cleanup_task(interval: int = 300):
    """
    Background task to periodically clean up expired cache entries.
    
    Args:
        interval: Cleanup interval in seconds
    """
    cache = get_cache()
    
    while True:
        await asyncio.sleep(interval)
        try:
            removed = await cache.cleanup_expired()
            if removed > 0:
                logger.info(f"Cache cleanup: removed {removed} expired entries")
        except Exception as e:
            logger.error(f"Error during cache cleanup: {e}")


__all__ = [
    "SimpleCache",
    "get_cache",
    "cached",
    "cache_cleanup_task",
]
