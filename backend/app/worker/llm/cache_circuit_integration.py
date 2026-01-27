"""
Cache-Circuit Breaker Integration Layer

P0-1 Fix: Cache와 Circuit Breaker의 상태 일관성 보장

문제:
- Cache hit 시 Circuit Breaker에 성공이 기록되지 않음
- Circuit이 OPEN 상태여도 Cache에서 응답 가능해야 함
- 두 시스템의 독립적 동작으로 상태 왜곡 발생

해결:
- CacheCircuitIntegration 클래스로 두 시스템 통합
- Cache hit 시 Circuit 상태 업데이트 (optional)
- Circuit OPEN 상태에서도 Cache 조회 허용

Usage:
    from app.worker.llm.cache_circuit_integration import get_cache_circuit

    integration = get_cache_circuit()

    # 통합된 조회 (Cache 우선, Circuit 상태 연동)
    result = await integration.get_with_fallback(
        operation=CacheOperation.PROFILE_EXTRACTION,
        provider="perplexity",
        query="...",
        context={...},
        fallback_fn=async_fetch_function,
    )
"""

import asyncio
from dataclasses import dataclass
from typing import Any, Callable, Optional, Awaitable
from enum import Enum

from app.worker.llm.cache import LLMCache, CacheOperation, get_llm_cache
from app.worker.llm.circuit_breaker import (
    CircuitBreakerManager,
    CircuitState,
    CircuitOpenError,
    get_circuit_breaker_manager,
)
from app.worker.tracing import get_logger, LogEvents

logger = get_logger("CacheCircuitIntegration")


class FetchResult(str, Enum):
    """조회 결과 유형"""
    CACHE_HIT = "cache_hit"
    FETCH_SUCCESS = "fetch_success"
    CIRCUIT_OPEN_CACHE_HIT = "circuit_open_cache_hit"
    CIRCUIT_OPEN_NO_CACHE = "circuit_open_no_cache"
    FETCH_FAILED = "fetch_failed"


@dataclass
class IntegrationResult:
    """통합 조회 결과"""
    data: Optional[Any]
    result_type: FetchResult
    provider: str
    from_cache: bool
    circuit_state: CircuitState
    error_message: Optional[str] = None


class CacheCircuitIntegration:
    """
    Cache와 Circuit Breaker 통합 레이어

    Features:
    - Cache hit 시 Circuit 성공 기록 (optional, 기본 비활성)
    - Circuit OPEN 시에도 Cache 조회 허용 (graceful degradation)
    - 통합 메트릭 및 로깅
    """

    def __init__(
        self,
        cache: Optional[LLMCache] = None,
        circuit_manager: Optional[CircuitBreakerManager] = None,
        record_cache_hit_as_success: bool = False,
    ):
        """
        Args:
            cache: LLM Cache 인스턴스
            circuit_manager: Circuit Breaker Manager
            record_cache_hit_as_success: Cache hit를 Circuit 성공으로 기록할지 여부
                - True: Cache hit 시 Circuit failure count 리셋 (공격적)
                - False: Cache hit는 Circuit 상태에 영향 없음 (보수적, 기본값)
        """
        self._cache = cache
        self._circuit_manager = circuit_manager
        self._record_cache_hit_as_success = record_cache_hit_as_success

    @property
    def cache(self) -> LLMCache:
        if self._cache is None:
            self._cache = get_llm_cache()
        return self._cache

    @property
    def circuit_manager(self) -> CircuitBreakerManager:
        if self._circuit_manager is None:
            self._circuit_manager = get_circuit_breaker_manager()
        return self._circuit_manager

    async def get_with_fallback(
        self,
        operation: CacheOperation,
        provider: str,
        query: str,
        context: Optional[dict],
        fallback_fn: Callable[[], Awaitable[Any]],
        cache_result: bool = True,
        ttl_override: Optional[int] = None,
    ) -> IntegrationResult:
        """
        Cache 우선 조회 + Circuit Breaker 연동

        1. Cache 조회 (Circuit 상태와 무관하게 항상 시도)
        2. Cache miss 시:
           - Circuit CLOSED/HALF_OPEN: fallback_fn 실행
           - Circuit OPEN: CircuitOpenError 또는 None 반환
        3. 결과 캐싱 및 Circuit 상태 업데이트

        Args:
            operation: Cache operation type
            provider: LLM provider name (for circuit breaker)
            query: Cache key query
            context: Cache key context
            fallback_fn: Cache miss 시 실행할 비동기 함수
            cache_result: 결과를 캐시할지 여부
            ttl_override: TTL 오버라이드

        Returns:
            IntegrationResult: 통합 결과
        """
        circuit = self.circuit_manager.get_breaker(provider)
        circuit_state = circuit.get_status().state

        # Step 1: Cache 조회 (항상 시도)
        cached = await self.cache.get(operation, query, context)

        if cached is not None:
            # Cache hit
            result_type = FetchResult.CACHE_HIT

            # Circuit이 OPEN이었다면 특별 처리
            if circuit_state == CircuitState.OPEN:
                result_type = FetchResult.CIRCUIT_OPEN_CACHE_HIT
                logger.info(
                    "cache_hit_circuit_open",
                    operation=operation.value,
                    provider=provider,
                    message="Cache hit while circuit is OPEN - serving stale data",
                )

            # Cache hit를 성공으로 기록 (설정에 따라)
            if self._record_cache_hit_as_success:
                circuit.record_success()
                logger.debug(
                    "cache_hit_recorded_as_success",
                    operation=operation.value,
                    provider=provider,
                )

            logger.info(
                LogEvents.LLM_CACHE_HIT,
                operation=operation.value,
                provider=provider,
                result_type=result_type.value,
            )

            return IntegrationResult(
                data=cached,
                result_type=result_type,
                provider=provider,
                from_cache=True,
                circuit_state=circuit_state,
            )

        # Step 2: Cache miss - Circuit 상태 확인
        logger.debug(
            LogEvents.LLM_CACHE_MISS,
            operation=operation.value,
            provider=provider,
        )

        if not circuit.is_available():
            # Circuit OPEN - fallback 불가
            logger.warning(
                "circuit_open_cache_miss",
                operation=operation.value,
                provider=provider,
                cooldown_remaining=circuit.get_status().cooldown_remaining,
            )
            return IntegrationResult(
                data=None,
                result_type=FetchResult.CIRCUIT_OPEN_NO_CACHE,
                provider=provider,
                from_cache=False,
                circuit_state=circuit_state,
                error_message=f"Circuit breaker OPEN for {provider}",
            )

        # Step 3: Fallback 실행
        try:
            data = await fallback_fn()

            # 성공 기록
            circuit.record_success()

            # 결과 캐싱
            if cache_result and data is not None:
                await self.cache.set(
                    operation, query, context, data,
                    ttl_override=ttl_override,
                )

            logger.info(
                LogEvents.LLM_CALL_SUCCESS,
                operation=operation.value,
                provider=provider,
                cached=cache_result,
            )

            return IntegrationResult(
                data=data,
                result_type=FetchResult.FETCH_SUCCESS,
                provider=provider,
                from_cache=False,
                circuit_state=circuit_state,
            )

        except Exception as e:
            # 실패 기록
            circuit.record_failure(str(e))

            logger.error(
                LogEvents.LLM_CALL_FAILED,
                operation=operation.value,
                provider=provider,
                error=str(e),
            )

            return IntegrationResult(
                data=None,
                result_type=FetchResult.FETCH_FAILED,
                provider=provider,
                from_cache=False,
                circuit_state=circuit.get_status().state,  # 업데이트된 상태
                error_message=str(e),
            )

    def get_unified_status(self) -> dict:
        """Cache와 Circuit의 통합 상태 조회"""
        circuit_status = self.circuit_manager.get_all_status()

        return {
            "circuit_breakers": {
                provider: {
                    "state": status.state.value,
                    "failure_count": status.failure_count,
                    "cooldown_remaining": status.cooldown_remaining,
                }
                for provider, status in circuit_status.items()
            },
            "integration_config": {
                "record_cache_hit_as_success": self._record_cache_hit_as_success,
            },
        }

    async def get_unified_status_with_cache(self) -> dict:
        """Cache 통계 포함 통합 상태 조회"""
        status = self.get_unified_status()

        try:
            cache_stats = await self.cache.get_stats()
            status["cache"] = cache_stats
        except Exception as e:
            status["cache_error"] = str(e)

        return status


# ============================================================================
# Singleton Instance
# ============================================================================

_integration_instance: Optional[CacheCircuitIntegration] = None


def get_cache_circuit(
    record_cache_hit_as_success: bool = False,
) -> CacheCircuitIntegration:
    """Get singleton CacheCircuitIntegration instance"""
    global _integration_instance
    if _integration_instance is None:
        _integration_instance = CacheCircuitIntegration(
            record_cache_hit_as_success=record_cache_hit_as_success,
        )
    return _integration_instance


def reset_cache_circuit() -> None:
    """Reset singleton instance (for testing)"""
    global _integration_instance
    _integration_instance = None
