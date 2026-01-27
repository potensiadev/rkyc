"""
LLM Response Caching for rKYC

2-Layer Cache Architecture:
- Layer 1: Memory LRU (fast, limited size)
- Layer 2: Redis (persistent across workers, larger capacity)

Cache Key Generation:
- operation + query_hash + context_hash

TTL Configuration per Operation Type:
- PROFILE_EXTRACTION: 7 days (stable data)
- SIGNAL_EXTRACTION: 1 day (needs freshness)
- VALIDATION: 1 hour (context-sensitive)
- EMBEDDING: 30 days (deterministic)

Usage:
    from app.worker.llm.cache import LLMCache, CacheConfig

    cache = LLMCache()

    # Try to get cached response
    cached = await cache.get("profile_extraction", query, context)
    if cached:
        return cached

    # Call LLM
    response = await llm_call(...)

    # Cache the response
    await cache.set("profile_extraction", query, context, response)
"""

import hashlib
import json
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
import asyncio
import redis.asyncio as redis

from app.worker.tracing import get_logger, LogEvents

logger = get_logger("LLMCache")


class CacheOperation(str, Enum):
    """LLM operation types with different caching strategies"""
    PROFILE_EXTRACTION = "profile_extraction"
    SIGNAL_EXTRACTION = "signal_extraction"
    VALIDATION = "validation"
    EMBEDDING = "embedding"
    CONSENSUS = "consensus"
    DOCUMENT_PARSING = "document_parsing"
    INSIGHT_GENERATION = "insight_generation"


@dataclass
class CacheConfig:
    """
    Cache configuration per operation type

    P1-1: Configuration 외부화 - settings에서 읽기
    """

    # TTL in seconds (will be overridden by settings if available)
    TTL_CONFIG: dict[CacheOperation, int] = field(default_factory=lambda: {
        CacheOperation.PROFILE_EXTRACTION: 7 * 24 * 3600,    # 7 days
        CacheOperation.SIGNAL_EXTRACTION: 24 * 3600,         # 1 day
        CacheOperation.VALIDATION: 3600,                      # 1 hour
        CacheOperation.EMBEDDING: 30 * 24 * 3600,            # 30 days
        CacheOperation.CONSENSUS: 24 * 3600,                 # 1 day
        CacheOperation.DOCUMENT_PARSING: 7 * 24 * 3600,      # 7 days
        CacheOperation.INSIGHT_GENERATION: 12 * 3600,        # 12 hours
    })

    # Memory LRU cache size per operation
    MEMORY_CACHE_SIZE: int = 100

    # Redis key prefix
    REDIS_KEY_PREFIX: str = "rkyc:llm:cache"

    # Redis DB number for cache (separate from Celery)
    REDIS_CACHE_DB: int = 2

    def __post_init__(self):
        """P1-1: Load TTL settings from config if available"""
        try:
            from app.core.config import settings
            self.TTL_CONFIG = {
                CacheOperation.PROFILE_EXTRACTION: settings.LLM_CACHE_TTL_PROFILE,
                CacheOperation.SIGNAL_EXTRACTION: settings.LLM_CACHE_TTL_SIGNAL,
                CacheOperation.VALIDATION: settings.LLM_CACHE_TTL_VALIDATION,
                CacheOperation.EMBEDDING: settings.LLM_CACHE_TTL_EMBEDDING,
                CacheOperation.CONSENSUS: settings.LLM_CACHE_TTL_CONSENSUS,
                CacheOperation.DOCUMENT_PARSING: settings.LLM_CACHE_TTL_DOCUMENT,
                CacheOperation.INSIGHT_GENERATION: settings.LLM_CACHE_TTL_INSIGHT,
            }
            self.MEMORY_CACHE_SIZE = settings.LLM_CACHE_MEMORY_SIZE
            self.REDIS_CACHE_DB = settings.LLM_CACHE_REDIS_DB
        except Exception as e:
            logger.warning(f"Failed to load cache config from settings: {e}, using defaults")

    def get_ttl(self, operation: CacheOperation) -> int:
        """Get TTL for operation type"""
        return self.TTL_CONFIG.get(operation, 3600)  # default 1 hour


class MemoryLRUCache:
    """Thread-safe LRU cache for fast in-memory caching"""

    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache, returns None if not found or expired"""
        async with self._lock:
            if key not in self._cache:
                return None

            value, expires_at = self._cache[key]

            # Check expiration
            if expires_at < time.time():
                del self._cache[key]
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            return value

    async def set(self, key: str, value: Any, ttl: int) -> None:
        """Set value in cache with TTL"""
        async with self._lock:
            expires_at = time.time() + ttl

            # Remove oldest if at capacity
            if key not in self._cache and len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)

            self._cache[key] = (value, expires_at)
            self._cache.move_to_end(key)

    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def clear(self) -> None:
        """Clear all cache entries"""
        async with self._lock:
            self._cache.clear()

    @property
    def size(self) -> int:
        """Current cache size"""
        return len(self._cache)


class LLMCache:
    """
    2-Layer LLM Response Cache

    Layer 1: Memory LRU (fast, per-worker)
    Layer 2: Redis (shared across workers)
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        config: Optional[CacheConfig] = None
    ):
        self.config = config or CacheConfig()
        self._redis_url = redis_url
        self._redis: Optional[redis.Redis] = None

        # Per-operation memory caches
        self._memory_caches: dict[CacheOperation, MemoryLRUCache] = {
            op: MemoryLRUCache(self.config.MEMORY_CACHE_SIZE)
            for op in CacheOperation
        }

        self._initialized = False

    async def initialize(self) -> None:
        """Initialize Redis connection"""
        if self._initialized:
            return

        if self._redis_url is None:
            from app.core.config import settings
            # Use separate DB for cache
            base_url = settings.REDIS_URL.rstrip("/0123456789")
            self._redis_url = f"{base_url}/{self.config.REDIS_CACHE_DB}"

        try:
            self._redis = redis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            # Test connection
            await self._redis.ping()
            self._initialized = True
            logger.info("llm_cache_initialized", redis_url=self._redis_url)
        except Exception as e:
            logger.warning(
                "llm_cache_redis_unavailable",
                error=str(e),
                fallback="memory_only"
            )
            self._redis = None
            self._initialized = True

    def _generate_cache_key(
        self,
        operation: CacheOperation,
        query: str,
        context: Optional[dict] = None
    ) -> str:
        """Generate deterministic cache key"""
        # Normalize query
        query_normalized = query.strip().lower()
        query_hash = hashlib.sha256(query_normalized.encode()).hexdigest()[:16]

        # Normalize context
        if context:
            # Sort keys for deterministic hashing
            context_str = json.dumps(context, sort_keys=True, ensure_ascii=False)
            context_hash = hashlib.sha256(context_str.encode()).hexdigest()[:16]
        else:
            context_hash = "none"

        return f"{self.config.REDIS_KEY_PREFIX}:{operation.value}:{query_hash}:{context_hash}"

    async def get(
        self,
        operation: CacheOperation,
        query: str,
        context: Optional[dict] = None
    ) -> Optional[dict]:
        """
        Get cached LLM response

        Checks Layer 1 (Memory) first, then Layer 2 (Redis)
        """
        await self.initialize()

        cache_key = self._generate_cache_key(operation, query, context)
        memory_cache = self._memory_caches[operation]

        # Layer 1: Memory cache
        cached = await memory_cache.get(cache_key)
        if cached is not None:
            logger.debug(
                LogEvents.LLM_CACHE_HIT,
                operation=operation.value,
                layer="memory",
                key=cache_key[:32]
            )
            return cached

        # Layer 2: Redis cache
        if self._redis:
            try:
                redis_value = await self._redis.get(cache_key)
                if redis_value:
                    cached = json.loads(redis_value)

                    # Promote to memory cache
                    ttl = self.config.get_ttl(operation)
                    await memory_cache.set(cache_key, cached, ttl)

                    logger.debug(
                        LogEvents.LLM_CACHE_HIT,
                        operation=operation.value,
                        layer="redis",
                        key=cache_key[:32]
                    )
                    return cached
            except Exception as e:
                logger.warning(
                    "llm_cache_redis_get_error",
                    error=str(e),
                    key=cache_key[:32]
                )

        logger.debug(
            LogEvents.LLM_CACHE_MISS,
            operation=operation.value,
            key=cache_key[:32]
        )
        return None

    async def set(
        self,
        operation: CacheOperation,
        query: str,
        context: Optional[dict],
        response: dict,
        ttl_override: Optional[int] = None
    ) -> bool:
        """
        Cache LLM response in both layers

        Args:
            operation: Operation type
            query: The query/prompt
            context: Additional context used in the call
            response: LLM response to cache
            ttl_override: Optional TTL override

        Returns:
            True if cached successfully (at least in memory)
        """
        await self.initialize()

        cache_key = self._generate_cache_key(operation, query, context)
        ttl = ttl_override or self.config.get_ttl(operation)
        memory_cache = self._memory_caches[operation]

        # Layer 1: Memory cache (always)
        await memory_cache.set(cache_key, response, ttl)

        # Layer 2: Redis cache (if available)
        if self._redis:
            try:
                await self._redis.setex(
                    cache_key,
                    ttl,
                    json.dumps(response, ensure_ascii=False)
                )
                logger.debug(
                    LogEvents.CACHE_SET,
                    operation=operation.value,
                    key=cache_key[:32],
                    ttl=ttl,
                    layers=["memory", "redis"]
                )
                return True
            except Exception as e:
                logger.warning(
                    "llm_cache_redis_set_error",
                    error=str(e),
                    key=cache_key[:32]
                )

        logger.debug(
            LogEvents.CACHE_SET,
            operation=operation.value,
            key=cache_key[:32],
            ttl=ttl,
            layers=["memory"]
        )
        return True

    async def invalidate(
        self,
        operation: CacheOperation,
        query: str,
        context: Optional[dict] = None
    ) -> bool:
        """Invalidate cache entry"""
        await self.initialize()

        cache_key = self._generate_cache_key(operation, query, context)
        memory_cache = self._memory_caches[operation]

        # Invalidate memory
        await memory_cache.delete(cache_key)

        # Invalidate Redis
        if self._redis:
            try:
                await self._redis.delete(cache_key)
            except Exception as e:
                logger.warning(
                    "llm_cache_redis_delete_error",
                    error=str(e),
                    key=cache_key[:32]
                )

        logger.debug(
            LogEvents.CACHE_INVALIDATE,
            operation=operation.value,
            key=cache_key[:32]
        )
        return True

    async def invalidate_by_pattern(
        self,
        operation: Optional[CacheOperation] = None,
        pattern_suffix: str = "*"
    ) -> int:
        """
        Invalidate cache entries by pattern

        Args:
            operation: Optional operation type filter
            pattern_suffix: Redis key pattern suffix

        Returns:
            Number of keys invalidated
        """
        await self.initialize()

        # Clear memory caches
        if operation:
            await self._memory_caches[operation].clear()
            count = 1
        else:
            for cache in self._memory_caches.values():
                await cache.clear()
            count = len(self._memory_caches)

        # Clear Redis by pattern
        if self._redis:
            try:
                if operation:
                    pattern = f"{self.config.REDIS_KEY_PREFIX}:{operation.value}:{pattern_suffix}"
                else:
                    pattern = f"{self.config.REDIS_KEY_PREFIX}:{pattern_suffix}"

                cursor = 0
                deleted = 0
                while True:
                    cursor, keys = await self._redis.scan(cursor, match=pattern, count=100)
                    if keys:
                        deleted += await self._redis.delete(*keys)
                    if cursor == 0:
                        break

                count = deleted
                logger.info(
                    "llm_cache_invalidate_pattern",
                    pattern=pattern,
                    deleted=deleted
                )
            except Exception as e:
                logger.warning(
                    "llm_cache_redis_pattern_delete_error",
                    error=str(e)
                )

        return count

    async def get_stats(self) -> dict:
        """Get cache statistics"""
        await self.initialize()

        stats = {
            "memory": {
                op.value: cache.size
                for op, cache in self._memory_caches.items()
            },
            "redis_available": self._redis is not None
        }

        if self._redis:
            try:
                # Count Redis keys by operation
                redis_counts = {}
                for op in CacheOperation:
                    pattern = f"{self.config.REDIS_KEY_PREFIX}:{op.value}:*"
                    count = 0
                    cursor = 0
                    while True:
                        cursor, keys = await self._redis.scan(cursor, match=pattern, count=100)
                        count += len(keys)
                        if cursor == 0:
                            break
                    redis_counts[op.value] = count

                stats["redis"] = redis_counts
            except Exception as e:
                stats["redis_error"] = str(e)

        return stats

    async def close(self) -> None:
        """Close Redis connection"""
        if self._redis:
            await self._redis.close()
            self._redis = None
            self._initialized = False


# Singleton instance
_cache_instance: Optional[LLMCache] = None


def get_llm_cache() -> LLMCache:
    """Get singleton LLM cache instance"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = LLMCache()
    return _cache_instance


async def reset_llm_cache() -> None:
    """Reset singleton cache instance (for testing)"""
    global _cache_instance
    if _cache_instance:
        await _cache_instance.close()
    _cache_instance = None
