"""
Circuit Breaker Pattern for LLM Providers

PRD v1.2 설정:
- perplexity: failure_threshold=3, cooldown=300s
- gemini: failure_threshold=3, cooldown=300s
- claude: failure_threshold=2, cooldown=600s (더 보수적)

상태 전이:
- CLOSED: 정상 동작
- OPEN: 차단 (cooldown 대기)
- HALF_OPEN: 테스트 요청 허용

v1.3 변경사항:
- Redis 영속화 지원 (Worker 재시작 시에도 상태 유지)
"""

import json
import logging
import time
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Optional, Callable

logger = logging.getLogger(__name__)

# Redis client (lazy initialization)
_redis_client = None


class CircuitBreakerRedisError(Exception):
    """Redis가 필수인데 연결 실패 시 발생"""
    pass


def _get_redis():
    """
    Redis 클라이언트 가져오기 (lazy initialization).

    v1.4 변경:
    - CIRCUIT_BREAKER_REQUIRE_REDIS=True (기본값)이면 Redis 연결 실패 시 예외 발생
    - 프로덕션 환경에서 Circuit Breaker 상태 손실 방지
    """
    global _redis_client
    if _redis_client is None:
        try:
            import redis
            from app.core.config import settings
            redis_url = getattr(settings, 'REDIS_URL', None)
            require_redis = getattr(settings, 'CIRCUIT_BREAKER_REQUIRE_REDIS', True)

            if redis_url:
                _redis_client = redis.from_url(redis_url, decode_responses=True)
                # Test connection
                _redis_client.ping()
                logger.info("[CircuitBreaker] Redis connection established for state persistence")
            else:
                if require_redis:
                    raise CircuitBreakerRedisError(
                        "REDIS_URL not configured but CIRCUIT_BREAKER_REQUIRE_REDIS=True. "
                        "Set CIRCUIT_BREAKER_REQUIRE_REDIS=False to use in-memory storage (not recommended for production)."
                    )
                logger.warning("[CircuitBreaker] REDIS_URL not configured, using in-memory storage (NOT RECOMMENDED)")
                _redis_client = False  # Mark as unavailable
        except CircuitBreakerRedisError:
            raise  # Re-raise our custom error
        except Exception as e:
            from app.core.config import settings
            require_redis = getattr(settings, 'CIRCUIT_BREAKER_REQUIRE_REDIS', True)
            if require_redis:
                raise CircuitBreakerRedisError(
                    f"Redis connection failed but CIRCUIT_BREAKER_REQUIRE_REDIS=True: {e}. "
                    "Set CIRCUIT_BREAKER_REQUIRE_REDIS=False to use in-memory storage (not recommended for production)."
                )
            logger.warning(f"[CircuitBreaker] Redis connection failed, using in-memory (NOT RECOMMENDED): {e}")
            _redis_client = False
    return _redis_client if _redis_client else None


class CircuitState(str, Enum):
    """Circuit Breaker 상태"""
    CLOSED = "CLOSED"  # 정상 동작
    OPEN = "OPEN"  # 차단됨
    HALF_OPEN = "HALF_OPEN"  # 테스트 중


@dataclass
class CircuitConfig:
    """Circuit Breaker 설정"""
    failure_threshold: int = 3  # 연속 실패 횟수
    cooldown_seconds: int = 300  # 차단 시간 (초)
    half_open_requests: int = 1  # 테스트 요청 수


@dataclass
class CircuitStatus:
    """Circuit Breaker 상태 정보"""
    provider: str
    state: CircuitState
    failure_count: int
    success_count: int
    last_failure_at: Optional[str]
    last_success_at: Optional[str]
    opened_at: Optional[str]
    cooldown_remaining: int  # 남은 cooldown 시간 (초)
    config: dict


@dataclass
class CircuitMetrics:
    """Circuit Breaker 메트릭"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rejected_requests: int = 0  # OPEN 상태에서 거부된 요청
    half_open_requests: int = 0


class CircuitBreaker:
    """
    Circuit Breaker for Individual Provider

    상태 전이:
    CLOSED → OPEN: failure_count >= failure_threshold
    OPEN → HALF_OPEN: cooldown_seconds 경과
    HALF_OPEN → CLOSED: 테스트 성공
    HALF_OPEN → OPEN: 테스트 실패

    Redis 영속화:
    - 상태 변경 시 Redis에 저장
    - 초기화 시 Redis에서 상태 복원
    """

    REDIS_KEY_PREFIX = "rkyc:circuit_breaker:"

    def __init__(self, provider: str, config: CircuitConfig, use_redis: bool = True):
        self.provider = provider
        self.config = config
        self._use_redis = use_redis
        self._lock = threading.Lock()

        # 기본 상태 초기화
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.half_open_successes = 0
        self.last_failure_at: Optional[float] = None
        self.last_success_at: Optional[float] = None
        self.opened_at: Optional[float] = None
        self.metrics = CircuitMetrics()

        # Redis에서 상태 복원 시도
        if use_redis:
            self._restore_from_redis()

    def _get_redis_key(self) -> str:
        """Redis 키 생성"""
        return f"{self.REDIS_KEY_PREFIX}{self.provider}"

    def _restore_from_redis(self):
        """Redis에서 상태 복원"""
        redis = _get_redis()
        if not redis:
            return

        try:
            key = self._get_redis_key()
            data = redis.get(key)
            if data:
                state_dict = json.loads(data)
                self.state = CircuitState(state_dict.get("state", "CLOSED"))
                self.failure_count = state_dict.get("failure_count", 0)
                self.success_count = state_dict.get("success_count", 0)
                self.half_open_successes = state_dict.get("half_open_successes", 0)
                self.last_failure_at = state_dict.get("last_failure_at")
                self.last_success_at = state_dict.get("last_success_at")
                self.opened_at = state_dict.get("opened_at")

                logger.info(
                    f"[CircuitBreaker:{self.provider}] State restored from Redis: "
                    f"state={self.state.value}, failures={self.failure_count}"
                )
        except Exception as e:
            logger.warning(f"[CircuitBreaker:{self.provider}] Failed to restore from Redis: {e}")

    def _save_to_redis(self):
        """Redis에 상태 저장"""
        if not self._use_redis:
            return

        redis = _get_redis()
        if not redis:
            return

        try:
            key = self._get_redis_key()
            state_dict = {
                "state": self.state.value,
                "failure_count": self.failure_count,
                "success_count": self.success_count,
                "half_open_successes": self.half_open_successes,
                "last_failure_at": self.last_failure_at,
                "last_success_at": self.last_success_at,
                "opened_at": self.opened_at,
                "updated_at": time.time(),
            }

            # TTL: cooldown 시간의 2배 (OPEN 상태가 만료되어도 일정 시간 유지)
            ttl = self.config.cooldown_seconds * 2
            redis.setex(key, ttl, json.dumps(state_dict))

            logger.debug(f"[CircuitBreaker:{self.provider}] State saved to Redis")
        except Exception as e:
            logger.warning(f"[CircuitBreaker:{self.provider}] Failed to save to Redis: {e}")

    def is_available(self) -> bool:
        """요청 허용 여부 확인"""
        with self._lock:
            self._check_state_transition()

            if self.state == CircuitState.CLOSED:
                return True

            if self.state == CircuitState.OPEN:
                self.metrics.rejected_requests += 1
                return False

            if self.state == CircuitState.HALF_OPEN:
                # HALF_OPEN에서는 제한된 요청만 허용
                if self.half_open_successes < self.config.half_open_requests:
                    self.metrics.half_open_requests += 1
                    return True
                return False

            return False

    def record_success(self):
        """성공 기록"""
        with self._lock:
            self.metrics.total_requests += 1
            self.metrics.successful_requests += 1
            self.success_count += 1
            self.last_success_at = time.time()

            if self.state == CircuitState.HALF_OPEN:
                self.half_open_successes += 1
                if self.half_open_successes >= self.config.half_open_requests:
                    self._transition_to_closed()
            elif self.state == CircuitState.CLOSED:
                # 성공 시 실패 카운트 리셋
                self.failure_count = 0

            self._save_to_redis()
            logger.debug(f"[CircuitBreaker:{self.provider}] Success recorded, state={self.state}")

    def record_failure(self, error: Optional[str] = None):
        """실패 기록"""
        with self._lock:
            self.metrics.total_requests += 1
            self.metrics.failed_requests += 1
            self.failure_count += 1
            self.last_failure_at = time.time()

            if self.state == CircuitState.HALF_OPEN:
                # HALF_OPEN에서 실패하면 다시 OPEN
                self._transition_to_open()
                logger.warning(
                    f"[CircuitBreaker:{self.provider}] HALF_OPEN → OPEN (test failed): {error}"
                )
            elif self.state == CircuitState.CLOSED:
                if self.failure_count >= self.config.failure_threshold:
                    self._transition_to_open()
                    logger.warning(
                        f"[CircuitBreaker:{self.provider}] CLOSED → OPEN "
                        f"(failures={self.failure_count}): {error}"
                    )

            self._save_to_redis()

    def get_status(self) -> CircuitStatus:
        """현재 상태 조회"""
        with self._lock:
            self._check_state_transition()

            cooldown_remaining = 0
            if self.state == CircuitState.OPEN and self.opened_at:
                elapsed = time.time() - self.opened_at
                cooldown_remaining = max(0, int(self.config.cooldown_seconds - elapsed))

            return CircuitStatus(
                provider=self.provider,
                state=self.state,
                failure_count=self.failure_count,
                success_count=self.success_count,
                last_failure_at=datetime.fromtimestamp(self.last_failure_at).isoformat() if self.last_failure_at else None,
                last_success_at=datetime.fromtimestamp(self.last_success_at).isoformat() if self.last_success_at else None,
                opened_at=datetime.fromtimestamp(self.opened_at).isoformat() if self.opened_at else None,
                cooldown_remaining=cooldown_remaining,
                config={
                    "failure_threshold": self.config.failure_threshold,
                    "cooldown_seconds": self.config.cooldown_seconds,
                    "half_open_requests": self.config.half_open_requests,
                },
            )

    def reset(self):
        """수동 리셋"""
        with self._lock:
            self._transition_to_closed()
            self.failure_count = 0
            self._save_to_redis()
            logger.info(f"[CircuitBreaker:{self.provider}] Manually reset to CLOSED")

    def _check_state_transition(self):
        """상태 전이 확인 (lock 내부에서 호출)"""
        if self.state == CircuitState.OPEN and self.opened_at:
            elapsed = time.time() - self.opened_at
            if elapsed >= self.config.cooldown_seconds:
                self._transition_to_half_open()
                logger.info(
                    f"[CircuitBreaker:{self.provider}] OPEN → HALF_OPEN "
                    f"(cooldown={self.config.cooldown_seconds}s elapsed)"
                )

    def _transition_to_open(self):
        """OPEN 상태로 전이 (lock 내부에서 호출)"""
        self.state = CircuitState.OPEN
        self.opened_at = time.time()
        self.half_open_successes = 0

    def _transition_to_half_open(self):
        """HALF_OPEN 상태로 전이 (lock 내부에서 호출)"""
        self.state = CircuitState.HALF_OPEN
        self.half_open_successes = 0
        self._save_to_redis()

    def _transition_to_closed(self):
        """CLOSED 상태로 전이 (lock 내부에서 호출)"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.opened_at = None
        self.half_open_successes = 0


# ============================================================================
# Circuit Breaker Manager
# ============================================================================


class CircuitBreakerManager:
    """
    Multiple Provider Circuit Breaker Manager

    PRD v1.2 설정:
    - perplexity: threshold=3, cooldown=300s
    - gemini: threshold=3, cooldown=300s
    - claude: threshold=2, cooldown=600s

    v1.3: Redis 영속화 지원
    """

    # PRD v1.2 기본 설정
    DEFAULT_CONFIGS = {
        "perplexity": CircuitConfig(
            failure_threshold=3,
            cooldown_seconds=300,
            half_open_requests=1,
        ),
        "gemini": CircuitConfig(
            failure_threshold=3,
            cooldown_seconds=300,
            half_open_requests=1,
        ),
        "claude": CircuitConfig(
            failure_threshold=2,
            cooldown_seconds=600,
            half_open_requests=1,
        ),
    }

    def __init__(self, use_redis: bool = True):
        self._breakers: dict[str, CircuitBreaker] = {}
        self._lock = threading.Lock()
        self._use_redis = use_redis

        # 기본 provider 초기화
        for provider, config in self.DEFAULT_CONFIGS.items():
            self._breakers[provider] = CircuitBreaker(provider, config, use_redis=use_redis)

    def get_breaker(self, provider: str) -> CircuitBreaker:
        """Provider별 Circuit Breaker 조회"""
        with self._lock:
            if provider not in self._breakers:
                # 기본 설정으로 생성
                self._breakers[provider] = CircuitBreaker(
                    provider,
                    CircuitConfig(),
                    use_redis=self._use_redis,
                )
            return self._breakers[provider]

    def is_available(self, provider: str) -> bool:
        """Provider 사용 가능 여부"""
        return self.get_breaker(provider).is_available()

    def record_success(self, provider: str):
        """성공 기록"""
        self.get_breaker(provider).record_success()

    def record_failure(self, provider: str, error: Optional[str] = None):
        """실패 기록"""
        self.get_breaker(provider).record_failure(error)

    def get_all_status(self) -> dict[str, CircuitStatus]:
        """모든 provider 상태 조회"""
        with self._lock:
            return {
                provider: breaker.get_status()
                for provider, breaker in self._breakers.items()
            }

    def get_status(self, provider: str) -> CircuitStatus:
        """특정 provider 상태 조회"""
        return self.get_breaker(provider).get_status()

    def reset_all(self):
        """모든 Circuit Breaker 리셋"""
        with self._lock:
            for breaker in self._breakers.values():
                breaker.reset()
            logger.info("[CircuitBreakerManager] All breakers reset")

    def reset(self, provider: str):
        """특정 provider 리셋"""
        self.get_breaker(provider).reset()

    def execute_with_circuit_breaker(
        self,
        provider: str,
        func: Callable,
        *args,
        **kwargs,
    ):
        """
        Circuit Breaker로 함수 실행

        Args:
            provider: Provider 이름
            func: 실행할 함수
            *args, **kwargs: 함수 인자

        Returns:
            함수 실행 결과

        Raises:
            CircuitOpenError: Circuit이 OPEN 상태일 때
            원본 예외: 함수 실행 실패 시
        """
        breaker = self.get_breaker(provider)

        if not breaker.is_available():
            raise CircuitOpenError(
                f"Circuit breaker for {provider} is OPEN. "
                f"Retry after {breaker.get_status().cooldown_remaining}s"
            )

        try:
            result = func(*args, **kwargs)
            breaker.record_success()
            return result
        except Exception as e:
            breaker.record_failure(str(e))
            raise


class CircuitOpenError(Exception):
    """Circuit Breaker가 OPEN 상태일 때 발생"""
    pass


# ============================================================================
# Singleton Instance (P0-003 fix: Thread-safe)
# ============================================================================

_manager_instance: Optional[CircuitBreakerManager] = None
_manager_lock = threading.Lock()


def get_circuit_breaker_manager(use_redis: bool = True) -> CircuitBreakerManager:
    """
    CircuitBreakerManager 싱글톤 인스턴스 반환 (thread-safe).

    P0-003 fix: Double-checked locking pattern for thread safety
    in Celery multi-worker environment.
    """
    global _manager_instance

    # First check without lock (fast path)
    if _manager_instance is not None:
        return _manager_instance

    # Acquire lock for initialization
    with _manager_lock:
        # Double-check after acquiring lock
        if _manager_instance is None:
            _manager_instance = CircuitBreakerManager(use_redis=use_redis)
            logger.info("CircuitBreakerManager singleton initialized")

    return _manager_instance


def get_circuit_breaker(provider: str) -> CircuitBreaker:
    """특정 provider의 Circuit Breaker 반환"""
    return get_circuit_breaker_manager().get_breaker(provider)


def reset_circuit_breaker_manager():
    """테스트용 - 싱글톤 인스턴스 리셋 (thread-safe)"""
    global _manager_instance
    with _manager_lock:
        if _manager_instance is not None:
            _manager_instance.reset_all()
        _manager_instance = None
        logger.info("CircuitBreakerManager singleton reset")
