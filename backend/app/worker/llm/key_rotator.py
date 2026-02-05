"""
API Key Rotator

API 키 로테이션 매니저
- 라운드 로빈 기반 키 분배
- 실패한 키 일시 제외 (cooldown)
- Provider별 독립 관리 (Perplexity, Google)
- P0 Fix: Redis 기반 상태 공유 (Celery Worker 간 동기화)

Railway 환경변수:
- PERPLEXITY_API_KEY_1, PERPLEXITY_API_KEY_2, PERPLEXITY_API_KEY_3
- GOOGLE_API_KEY_1, GOOGLE_API_KEY_2, GOOGLE_API_KEY_3
"""

import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from threading import Lock

from app.core.config import settings

logger = logging.getLogger(__name__)


class KeyState(str, Enum):
    """키 상태"""
    AVAILABLE = "AVAILABLE"
    COOLDOWN = "COOLDOWN"


@dataclass
class KeyInfo:
    """개별 키 정보"""
    key: str
    index: int
    state: KeyState = KeyState.AVAILABLE
    failed_at: Optional[float] = None
    failure_count: int = 0
    success_count: int = 0

    def is_available(self, cooldown_seconds: int) -> bool:
        """키 사용 가능 여부"""
        if self.state == KeyState.AVAILABLE:
            return True
        if self.failed_at is None:
            return True
        elapsed = time.time() - self.failed_at
        return elapsed >= cooldown_seconds

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "state": self.state.value,
            "failed_at": self.failed_at,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
        }

    @classmethod
    def from_dict(cls, key: str, data: dict) -> "KeyInfo":
        return cls(
            key=key,
            index=data.get("index", 0),
            state=KeyState(data.get("state", "AVAILABLE")),
            failed_at=data.get("failed_at"),
            failure_count=data.get("failure_count", 0),
            success_count=data.get("success_count", 0),
        )


@dataclass
class ProviderKeyPool:
    """Provider별 키 풀 (In-Memory)"""
    provider: str
    keys: list[KeyInfo] = field(default_factory=list)
    current_index: int = 0
    cooldown_seconds: int = 300  # 5분
    _lock: Lock = field(default_factory=Lock)

    def add_key(self, key: str) -> None:
        """키 추가"""
        if key and key.strip():
            self.keys.append(KeyInfo(
                key=key.strip(),
                index=len(self.keys),
            ))

    def get_next_key(self) -> Optional[str]:
        """다음 사용 가능한 키 반환 (라운드 로빈)"""
        with self._lock:
            if not self.keys:
                return None

            # 한 바퀴 돌면서 사용 가능한 키 찾기
            for _ in range(len(self.keys)):
                key_info = self.keys[self.current_index]
                self.current_index = (self.current_index + 1) % len(self.keys)

                if key_info.is_available(self.cooldown_seconds):
                    logger.debug(
                        f"[KeyRotator] {self.provider}: Using key index {key_info.index}"
                    )
                    return key_info.key

            # 모든 키가 cooldown 중이면 가장 오래된 실패 키 반환
            oldest = min(self.keys, key=lambda k: k.failed_at or 0)
            logger.warning(
                f"[KeyRotator] {self.provider}: All keys in cooldown, using oldest failed key"
            )
            return oldest.key

    def mark_failed(self, key: str) -> None:
        """키 실패 마킹"""
        with self._lock:
            for key_info in self.keys:
                if key_info.key == key:
                    key_info.state = KeyState.COOLDOWN
                    key_info.failed_at = time.time()
                    key_info.failure_count += 1
                    logger.warning(
                        f"[KeyRotator] {self.provider}: Key {key_info.index} marked as failed "
                        f"(failures: {key_info.failure_count})"
                    )
                    break

    def mark_success(self, key: str) -> None:
        """키 성공 마킹"""
        with self._lock:
            for key_info in self.keys:
                if key_info.key == key:
                    key_info.state = KeyState.AVAILABLE
                    key_info.failed_at = None
                    key_info.success_count += 1
                    break

    def reset_all(self) -> None:
        """모든 키 상태 리셋"""
        with self._lock:
            for key_info in self.keys:
                key_info.state = KeyState.AVAILABLE
                key_info.failed_at = None

    def get_status(self) -> dict:
        """상태 조회"""
        with self._lock:
            available_count = sum(
                1 for k in self.keys if k.is_available(self.cooldown_seconds)
            )

            def _calc_cooldown_remaining(key_info: KeyInfo) -> float:
                """cooldown_remaining 계산"""
                if key_info.failed_at is None:
                    return 0.0
                elapsed = time.time() - key_info.failed_at
                remaining = self.cooldown_seconds - elapsed
                return max(0.0, remaining)

            return {
                "provider": self.provider,
                "total_keys": len(self.keys),
                "available_keys": available_count,
                "cooldown_seconds": self.cooldown_seconds,
                "keys": [
                    {
                        "index": k.index,
                        "available": k.is_available(self.cooldown_seconds),
                        "state": k.state.value,
                        "failure_count": k.failure_count,
                        "success_count": k.success_count,
                        "cooldown_remaining": round(_calc_cooldown_remaining(k), 1),
                    }
                    for k in self.keys
                ],
            }


class RedisKeyPool:
    """
    P0 Fix: Redis 기반 키 풀 (Worker 간 상태 공유)

    Redis Hash 구조:
    - key_rotator:{provider}:keys -> {key_hash: json(KeyInfo)}
    - key_rotator:{provider}:index -> current_index (atomic increment)
    - key_rotator:{provider}:failed:{key_hash} -> TTL로 자동 만료
    """

    REDIS_PREFIX = "key_rotator"

    def __init__(
        self,
        provider: str,
        keys: list[str],
        cooldown_seconds: int = 300,
        redis_client=None,
    ):
        self.provider = provider
        self.cooldown_seconds = cooldown_seconds
        self._redis = redis_client
        self._keys = keys  # 원본 키 목록 (순서 유지)
        self._key_hashes = {self._hash_key(k): k for k in keys}
        self._fallback_pool: Optional[ProviderKeyPool] = None

    def _hash_key(self, key: str) -> str:
        """키를 해시로 변환 (보안상 원본 키를 Redis에 저장하지 않음)"""
        import hashlib
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    def _get_redis(self):
        """Redis 클라이언트 가져오기"""
        if self._redis:
            return self._redis
        try:
            import redis
            self._redis = redis.from_url(settings.REDIS_URL)
            # 연결 테스트
            self._redis.ping()
            return self._redis
        except Exception as e:
            logger.warning(f"[KeyRotator] Redis connection failed: {e}")
            return None

    def _get_fallback_pool(self) -> ProviderKeyPool:
        """Redis 불가 시 In-Memory Fallback"""
        if self._fallback_pool is None:
            self._fallback_pool = ProviderKeyPool(
                provider=self.provider,
                cooldown_seconds=self.cooldown_seconds,
            )
            for key in self._keys:
                self._fallback_pool.add_key(key)
            logger.warning(
                f"[KeyRotator] {self.provider}: Using in-memory fallback"
            )
        return self._fallback_pool

    def get_next_key(self) -> Optional[str]:
        """다음 사용 가능한 키 반환 (Redis 기반 라운드 로빈)"""
        if not self._keys:
            return None

        redis_client = self._get_redis()
        if not redis_client:
            return self._get_fallback_pool().get_next_key()

        try:
            # Atomic increment for round-robin index
            index_key = f"{self.REDIS_PREFIX}:{self.provider}:index"
            current_index = redis_client.incr(index_key)

            # 한 바퀴 돌면서 사용 가능한 키 찾기
            for offset in range(len(self._keys)):
                idx = (current_index + offset) % len(self._keys)
                key = self._keys[idx]
                key_hash = self._hash_key(key)

                # 실패 상태 확인 (TTL로 자동 관리)
                failed_key = f"{self.REDIS_PREFIX}:{self.provider}:failed:{key_hash}"
                if not redis_client.exists(failed_key):
                    logger.debug(
                        f"[KeyRotator] {self.provider}: Using key index {idx} (Redis)"
                    )
                    return key

            # 모든 키가 cooldown 중이면 첫 번째 키 반환
            logger.warning(
                f"[KeyRotator] {self.provider}: All keys in cooldown (Redis)"
            )
            return self._keys[0]

        except Exception as e:
            logger.warning(f"[KeyRotator] Redis error in get_next_key: {e}")
            return self._get_fallback_pool().get_next_key()

    def mark_failed(self, key: str) -> None:
        """키 실패 마킹 (TTL로 자동 cooldown)"""
        redis_client = self._get_redis()
        if not redis_client:
            self._get_fallback_pool().mark_failed(key)
            return

        try:
            key_hash = self._hash_key(key)
            failed_key = f"{self.REDIS_PREFIX}:{self.provider}:failed:{key_hash}"

            # 실패 횟수 증가 (SET + EXPIRE 원자적 수행)
            pipe = redis_client.pipeline()
            pipe.incr(failed_key)
            pipe.expire(failed_key, self.cooldown_seconds)
            results = pipe.execute()

            failure_count = results[0]
            logger.warning(
                f"[KeyRotator] {self.provider}: Key marked as failed (Redis), "
                f"failures: {failure_count}, cooldown: {self.cooldown_seconds}s"
            )
        except Exception as e:
            logger.warning(f"[KeyRotator] Redis error in mark_failed: {e}")
            self._get_fallback_pool().mark_failed(key)

    def mark_success(self, key: str) -> None:
        """키 성공 마킹 (cooldown 해제)"""
        redis_client = self._get_redis()
        if not redis_client:
            self._get_fallback_pool().mark_success(key)
            return

        try:
            key_hash = self._hash_key(key)
            failed_key = f"{self.REDIS_PREFIX}:{self.provider}:failed:{key_hash}"

            # 실패 상태 삭제
            redis_client.delete(failed_key)

            # 성공 횟수 증가 (선택적 - 통계용)
            success_key = f"{self.REDIS_PREFIX}:{self.provider}:success:{key_hash}"
            redis_client.incr(success_key)
        except Exception as e:
            logger.warning(f"[KeyRotator] Redis error in mark_success: {e}")
            self._get_fallback_pool().mark_success(key)

    def reset_all(self) -> None:
        """모든 키 상태 리셋"""
        redis_client = self._get_redis()
        if not redis_client:
            if self._fallback_pool:
                self._fallback_pool.reset_all()
            return

        try:
            # 모든 failed 키 삭제
            pattern = f"{self.REDIS_PREFIX}:{self.provider}:failed:*"
            keys = redis_client.keys(pattern)
            if keys:
                redis_client.delete(*keys)
            logger.info(f"[KeyRotator] {self.provider}: All keys reset (Redis)")
        except Exception as e:
            logger.warning(f"[KeyRotator] Redis error in reset_all: {e}")
            if self._fallback_pool:
                self._fallback_pool.reset_all()

    def get_status(self) -> dict:
        """상태 조회"""
        redis_client = self._get_redis()
        if not redis_client:
            return self._get_fallback_pool().get_status()

        try:
            keys_status = []
            available_count = 0

            for idx, key in enumerate(self._keys):
                key_hash = self._hash_key(key)
                failed_key = f"{self.REDIS_PREFIX}:{self.provider}:failed:{key_hash}"
                success_key = f"{self.REDIS_PREFIX}:{self.provider}:success:{key_hash}"

                # 실패 상태 및 TTL 확인
                failure_count = redis_client.get(failed_key)
                ttl = redis_client.ttl(failed_key)
                success_count = redis_client.get(success_key)

                is_available = ttl <= 0  # TTL 없거나 만료됨
                if is_available:
                    available_count += 1

                keys_status.append({
                    "index": idx,
                    "available": is_available,
                    "state": "COOLDOWN" if not is_available else "AVAILABLE",
                    "failure_count": int(failure_count) if failure_count else 0,
                    "success_count": int(success_count) if success_count else 0,
                    "cooldown_remaining": max(0, ttl) if ttl > 0 else 0,
                })

            return {
                "provider": self.provider,
                "total_keys": len(self._keys),
                "available_keys": available_count,
                "cooldown_seconds": self.cooldown_seconds,
                "storage": "redis",
                "keys": keys_status,
            }
        except Exception as e:
            logger.warning(f"[KeyRotator] Redis error in get_status: {e}")
            return self._get_fallback_pool().get_status()


class KeyRotator:
    """
    API Key Rotator Manager

    여러 Provider의 API 키를 관리하고 로테이션합니다.

    P0 Fix: Redis 기반 상태 공유
    - Celery worker 간 키 상태 동기화
    - 한 worker에서 실패 마킹하면 다른 worker도 즉시 인지
    - Redis 불가 시 In-Memory Fallback (기존 동작)

    사용법:
        rotator = get_key_rotator()
        key = rotator.get_key("perplexity")
        try:
            # API 호출
            rotator.mark_success("perplexity", key)
        except Exception:
            rotator.mark_failed("perplexity", key)
    """

    def __init__(self, use_redis: bool = True):
        self.use_redis = use_redis and settings.KEY_ROTATION_ENABLED
        self.pools: dict[str, RedisKeyPool | ProviderKeyPool] = {}
        self._initialize_pools()

    def _initialize_pools(self) -> None:
        """환경변수에서 키 로드"""
        cooldown = settings.KEY_ROTATION_FAILURE_COOLDOWN

        # Perplexity 키 수집
        perplexity_keys = []
        if settings.PERPLEXITY_API_KEY_1:
            perplexity_keys.append(settings.PERPLEXITY_API_KEY_1)
        if settings.PERPLEXITY_API_KEY_2:
            perplexity_keys.append(settings.PERPLEXITY_API_KEY_2)
        if settings.PERPLEXITY_API_KEY_3:
            perplexity_keys.append(settings.PERPLEXITY_API_KEY_3)
        if not perplexity_keys and settings.PERPLEXITY_API_KEY:
            perplexity_keys.append(settings.PERPLEXITY_API_KEY)

        # Google 키 수집
        google_keys = []
        if settings.GOOGLE_API_KEY_1:
            google_keys.append(settings.GOOGLE_API_KEY_1)
        if settings.GOOGLE_API_KEY_2:
            google_keys.append(settings.GOOGLE_API_KEY_2)
        if settings.GOOGLE_API_KEY_3:
            google_keys.append(settings.GOOGLE_API_KEY_3)
        if not google_keys and settings.GOOGLE_API_KEY:
            google_keys.append(settings.GOOGLE_API_KEY)

        # Pool 생성 (Redis 또는 In-Memory)
        if self.use_redis:
            self.pools["perplexity"] = RedisKeyPool(
                provider="perplexity",
                keys=perplexity_keys,
                cooldown_seconds=cooldown,
            )
            self.pools["google"] = RedisKeyPool(
                provider="google",
                keys=google_keys,
                cooldown_seconds=cooldown,
            )
            logger.info("[KeyRotator] Using Redis-based key rotation")
        else:
            perplexity_pool = ProviderKeyPool(
                provider="perplexity",
                cooldown_seconds=cooldown,
            )
            for key in perplexity_keys:
                perplexity_pool.add_key(key)
            self.pools["perplexity"] = perplexity_pool

            google_pool = ProviderKeyPool(
                provider="google",
                cooldown_seconds=cooldown,
            )
            for key in google_keys:
                google_pool.add_key(key)
            self.pools["google"] = google_pool
            logger.info("[KeyRotator] Using in-memory key rotation")

        # 로깅
        for provider, pool in self.pools.items():
            if isinstance(pool, RedisKeyPool):
                logger.info(
                    f"[KeyRotator] {provider}: Loaded {len(pool._keys)} keys (Redis)"
                )
            else:
                logger.info(
                    f"[KeyRotator] {provider}: Loaded {len(pool.keys)} keys (In-Memory)"
                )

    def get_key(self, provider: str) -> Optional[str]:
        """
        Provider의 다음 사용 가능한 키 반환

        Args:
            provider: "perplexity" 또는 "google"

        Returns:
            API 키 또는 None
        """
        if not settings.KEY_ROTATION_ENABLED:
            # 로테이션 비활성화 시 기본 키 반환
            if provider == "perplexity":
                return settings.PERPLEXITY_API_KEY
            elif provider == "google":
                return settings.GOOGLE_API_KEY
            return None

        pool = self.pools.get(provider)
        if not pool:
            logger.warning(f"[KeyRotator] Unknown provider: {provider}")
            return None

        return pool.get_next_key()

    def mark_failed(self, provider: str, key: str) -> None:
        """키 실패 마킹"""
        pool = self.pools.get(provider)
        if pool:
            pool.mark_failed(key)

    def mark_success(self, provider: str, key: str) -> None:
        """키 성공 마킹"""
        pool = self.pools.get(provider)
        if pool:
            pool.mark_success(key)

    def reset_provider(self, provider: str) -> None:
        """특정 Provider의 모든 키 리셋"""
        pool = self.pools.get(provider)
        if pool:
            pool.reset_all()
            logger.info(f"[KeyRotator] {provider}: All keys reset")

    def reset_all(self) -> None:
        """모든 Provider 리셋"""
        for pool in self.pools.values():
            pool.reset_all()
        logger.info("[KeyRotator] All providers reset")

    def get_status(self) -> dict:
        """전체 상태 조회"""
        return {
            "enabled": settings.KEY_ROTATION_ENABLED,
            "use_redis": self.use_redis,
            "providers": {
                provider: pool.get_status()
                for provider, pool in self.pools.items()
            },
        }


# ============================================================
# Singleton
# ============================================================

_key_rotator: Optional[KeyRotator] = None


def get_key_rotator() -> KeyRotator:
    """KeyRotator 싱글톤"""
    global _key_rotator
    if _key_rotator is None:
        _key_rotator = KeyRotator()
    return _key_rotator


def reset_key_rotator() -> None:
    """싱글톤 리셋 (테스트용)"""
    global _key_rotator
    _key_rotator = None
