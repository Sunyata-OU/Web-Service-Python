"""
Caching utilities and decorators for performance optimization.
"""

import functools
import hashlib
import json
import pickle
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

import redis
from src.config import get_settings
from src.logger import logger


class CacheManager:
    """Redis-based cache manager with multiple cache strategies."""

    def __init__(self):
        self.settings = get_settings()
        self.redis_client = None
        self._connect()

    def _connect(self):
        """Connect to Redis."""
        # Skip Redis connection in testing environment
        import os

        if os.environ.get("TESTING") == "true" or os.environ.get("ENVIRONMENT") == "testing":
            logger.info("Skipping Redis connection in test environment")
            self.redis_client = None
            return

        try:
            self.redis_client = redis.from_url(
                self.settings.redis_url,
                decode_responses=False,  # We handle encoding ourselves
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30,
            )
            # Test connection
            self.redis_client.ping()
            logger.info("Connected to Redis cache", redis_url=self.settings.redis_url)
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            self.redis_client = None

    def _ensure_connection(self) -> bool:
        """Ensure Redis connection is active."""
        if not self.redis_client:
            self._connect()

        if not self.redis_client:
            return False

        try:
            self.redis_client.ping()
            return True
        except Exception as e:
            logger.warning(f"Redis connection lost, reconnecting: {str(e)}")
            self._connect()
            return self.redis_client is not None

    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate a cache key from function arguments."""
        # Create a string representation of arguments
        key_data = {"args": args, "kwargs": sorted(kwargs.items()) if kwargs else {}}
        key_string = json.dumps(key_data, sort_keys=True, default=str)

        # Hash the key for consistent length
        key_hash = hashlib.md5(key_string.encode()).hexdigest()

        return f"{prefix}:{key_hash}"

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self._ensure_connection():
            return None

        try:
            value = self.redis_client.get(key)
            if value is not None:
                logger.debug(f"Cache HIT: {key}")
                return pickle.loads(value)
            else:
                logger.debug(f"Cache MISS: {key}")
                return None
        except Exception as e:
            logger.warning(f"Cache get error for key {key}: {str(e)}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None, nx: bool = False) -> bool:
        """Set value in cache."""
        if not self._ensure_connection():
            return False

        try:
            pickled_value = pickle.dumps(value)
            result = self.redis_client.set(key, pickled_value, ex=ttl, nx=nx)
            logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
            return bool(result)
        except Exception as e:
            logger.warning(f"Cache set error for key {key}: {str(e)}")
            return False

    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        if not self._ensure_connection():
            return False

        try:
            result = self.redis_client.delete(key)
            logger.debug(f"Cache DELETE: {key}")
            return result > 0
        except Exception as e:
            logger.warning(f"Cache delete error for key {key}: {str(e)}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern."""
        if not self._ensure_connection():
            return 0

        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                result = self.redis_client.delete(*keys)
                logger.debug(f"Cache DELETE pattern {pattern}: {result} keys")
                return result
            return 0
        except Exception as e:
            logger.warning(f"Cache delete pattern error for {pattern}: {str(e)}")
            return 0

    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if not self._ensure_connection():
            return False

        try:
            return bool(self.redis_client.exists(key))
        except Exception as e:
            logger.warning(f"Cache exists error for key {key}: {str(e)}")
            return False

    def get_ttl(self, key: str) -> Optional[int]:
        """Get TTL for key."""
        if not self._ensure_connection():
            return None

        try:
            ttl = self.redis_client.ttl(key)
            return ttl if ttl >= 0 else None
        except Exception as e:
            logger.warning(f"Cache TTL error for key {key}: {str(e)}")
            return None

    def increment(self, key: str, amount: int = 1, ttl: Optional[int] = None) -> Optional[int]:
        """Increment a counter in cache."""
        if not self._ensure_connection():
            return None

        try:
            result = self.redis_client.incr(key, amount)
            if ttl and result == amount:  # First increment, set TTL
                self.redis_client.expire(key, ttl)
            return result
        except Exception as e:
            logger.warning(f"Cache increment error for key {key}: {str(e)}")
            return None


# Global cache instance
cache = CacheManager()


def cached(
    ttl: int = 300,  # 5 minutes default
    prefix: str = "func",
    key_func: Optional[Callable] = None,
    skip_cache: Optional[Callable] = None,
):
    """
    Decorator to cache function results.

    Args:
        ttl: Time to live in seconds
        prefix: Cache key prefix
        key_func: Custom function to generate cache key
        skip_cache: Function that returns True to skip caching
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Check if we should skip cache
            if skip_cache and skip_cache(*args, **kwargs):
                return await func(*args, **kwargs)

            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = cache._generate_key(f"{prefix}:{func.__name__}", *args, **kwargs)

            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Execute function and cache result
            result = await func(*args, **kwargs)
            cache.set(cache_key, result, ttl=ttl)

            return result

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Check if we should skip cache
            if skip_cache and skip_cache(*args, **kwargs):
                return func(*args, **kwargs)

            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = cache._generate_key(f"{prefix}:{func.__name__}", *args, **kwargs)

            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl=ttl)

            return result

        # Return appropriate wrapper based on function type
        if hasattr(func, "__code__") and "await" in func.__code__.co_names:
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def cache_key_for_user(user_id: int, *args, **kwargs) -> str:
    """Generate cache key for user-specific data."""
    return cache._generate_key(f"user:{user_id}", *args, **kwargs)


def cache_key_for_model(model_name: str, model_id: int) -> str:
    """Generate cache key for model instances."""
    return f"model:{model_name}:{model_id}"


class SessionCache:
    """Request-scoped cache for expensive operations within a single request."""

    def __init__(self):
        self._cache: Dict[str, Any] = {}

    def get(self, key: str) -> Optional[Any]:
        """Get value from session cache."""
        return self._cache.get(key)

    def set(self, key: str, value: Any):
        """Set value in session cache."""
        self._cache[key] = value

    def clear(self):
        """Clear session cache."""
        self._cache.clear()


# Session cache dependency
def get_session_cache() -> SessionCache:
    """FastAPI dependency for request-scoped caching."""
    return SessionCache()


class QueryCache:
    """Specialized cache for database queries."""

    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager

    def cache_query_result(self, query: str, params: Dict[str, Any], result: Any, ttl: int = 300):
        """Cache database query result."""
        key = self._query_key(query, params)
        self.cache.set(key, result, ttl=ttl)

    def get_cached_query(self, query: str, params: Dict[str, Any]) -> Optional[Any]:
        """Get cached database query result."""
        key = self._query_key(query, params)
        return self.cache.get(key)

    def invalidate_table_cache(self, table_name: str):
        """Invalidate all cached queries for a table."""
        pattern = f"query:*{table_name}*"
        self.cache.delete_pattern(pattern)

    def _query_key(self, query: str, params: Dict[str, Any]) -> str:
        """Generate cache key for database query."""
        query_hash = hashlib.md5(query.encode()).hexdigest()
        params_hash = hashlib.md5(json.dumps(params, sort_keys=True, default=str).encode()).hexdigest()
        return f"query:{query_hash}:{params_hash}"


# Query cache instance
query_cache = QueryCache(cache)


class RateLimiter:
    """Redis-based rate limiter."""

    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager

    def is_allowed(self, identifier: str, max_requests: int, window_seconds: int, action: str = "request") -> bool:
        """Check if request is allowed under rate limit."""
        key = f"rate_limit:{action}:{identifier}"

        try:
            current = self.cache.increment(key, ttl=window_seconds)
            if current is None:
                return True  # Cache unavailable, allow request

            return current <= max_requests
        except Exception as e:
            logger.warning(f"Rate limiter error: {str(e)}")
            return True  # On error, allow request

    def get_current_usage(self, identifier: str, action: str = "request") -> int:
        """Get current usage count."""
        key = f"rate_limit:{action}:{identifier}"
        count = self.cache.get(key)
        return count if isinstance(count, int) else 0

    def get_reset_time(self, identifier: str, action: str = "request") -> Optional[datetime]:
        """Get when rate limit resets."""
        key = f"rate_limit:{action}:{identifier}"
        ttl = self.cache.get_ttl(key)
        if ttl:
            return datetime.utcnow() + timedelta(seconds=ttl)
        return None


# Rate limiter instance
rate_limiter = RateLimiter(cache)


def cached_property(ttl: int = 300):
    """Decorator for caching expensive property calculations."""

    def decorator(func: Callable) -> property:
        attr_name = f"_cached_{func.__name__}"

        def wrapper(self):
            # Check if we have a cached value
            if hasattr(self, attr_name):
                cached_value, cached_time = getattr(self, attr_name)
                if datetime.utcnow() - cached_time < timedelta(seconds=ttl):
                    return cached_value

            # Calculate new value and cache it
            result = func(self)
            setattr(self, attr_name, (result, datetime.utcnow()))
            return result

        return property(wrapper)

    return decorator


# Performance monitoring
class PerformanceMonitor:
    """Monitor and cache performance metrics."""

    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager

    def record_response_time(self, endpoint: str, duration_ms: float):
        """Record response time for an endpoint."""
        key = f"perf:response_time:{endpoint}"

        # Store last 100 response times
        times_key = f"{key}:times"
        try:
            # Add to list and trim to last 100
            self.cache.redis_client.lpush(times_key, duration_ms)
            self.cache.redis_client.ltrim(times_key, 0, 99)
            self.cache.redis_client.expire(times_key, 3600)  # 1 hour TTL
        except Exception as e:
            logger.warning(f"Performance monitoring error: {str(e)}")

    def get_avg_response_time(self, endpoint: str) -> Optional[float]:
        """Get average response time for endpoint."""
        key = f"perf:response_time:{endpoint}:times"

        try:
            times = self.cache.redis_client.lrange(key, 0, -1)
            if times:
                avg = sum(float(t) for t in times) / len(times)
                return round(avg, 2)
        except Exception as e:
            logger.warning(f"Performance monitoring error: {str(e)}")

        return None

    def get_slow_endpoints(self, threshold_ms: float = 1000) -> List[Dict[str, Any]]:
        """Get endpoints with slow response times."""
        pattern = "perf:response_time:*:times"
        slow_endpoints = []

        try:
            keys = self.cache.redis_client.keys(pattern)
            for key in keys:
                endpoint = key.decode().split(":")[2]  # Extract endpoint name
                avg_time = self.get_avg_response_time(endpoint)
                if avg_time and avg_time > threshold_ms:
                    slow_endpoints.append({"endpoint": endpoint, "avg_response_time_ms": avg_time})
        except Exception as e:
            logger.warning(f"Performance monitoring error: {str(e)}")

        return sorted(slow_endpoints, key=lambda x: x["avg_response_time_ms"], reverse=True)


# Performance monitor instance
perf_monitor = PerformanceMonitor(cache)
