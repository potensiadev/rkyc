"""
Multi-Search Provider Architecture
Perplexity 의존도 완화를 위한 검색 가능 LLM 2-Track 구성

Search Provider (검색 내장 LLM만 사용):
1. Perplexity (Primary) - 실시간 검색 + AI 요약
2. Gemini Grounding (Fallback) - Google Search 기반 LLM 검색

사용 중인 LLM: Perplexity, Gemini, OpenAI, Claude
- OpenAI/Claude는 검색 기능이 없어 분석/합성에만 사용
- 검색은 Perplexity → Gemini Grounding 2-Track으로 처리

Circuit Breaker 연동: Provider별 상태 관리
"""

import asyncio
import hashlib
import json
import logging
import os
import re
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

import httpx

from app.core.config import settings
from app.worker.llm.circuit_breaker import (
    CircuitBreakerManager,
    CircuitOpenError,
    get_circuit_breaker_manager,
)
from app.worker.llm.key_rotator import get_key_rotator, KeyRotator

logger = logging.getLogger(__name__)

# P0 Fix: Thread-safe event loop 관리
_thread_local = threading.local()
_event_loop_lock = threading.Lock()


def _get_or_create_event_loop() -> asyncio.AbstractEventLoop:
    """
    P0 Fix: Thread-safe event loop 관리

    스레드별로 독립된 event loop를 관리하여 race condition 방지.
    Lock으로 TOCTOU 버그 방지.
    """
    # 먼저 running loop 확인 (이미 async 컨텍스트인 경우)
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        pass

    # Thread-local storage에서 안전하게 loop 관리
    with _event_loop_lock:
        if hasattr(_thread_local, 'loop') and _thread_local.loop is not None:
            if not _thread_local.loop.is_closed():
                return _thread_local.loop

        # 새 loop 생성 및 저장
        loop = asyncio.new_event_loop()
        _thread_local.loop = loop
        return loop


class SearchProviderType(str, Enum):
    """검색 Provider 타입 (검색 내장 LLM만)"""
    PERPLEXITY = "perplexity"              # Primary - 실시간 검색 + AI 요약
    GEMINI_GROUNDING = "gemini_grounding"  # Fallback - Google Search 기반


@dataclass
class SearchResult:
    """통합 검색 결과"""
    provider: SearchProviderType
    content: str  # 검색 결과 텍스트
    citations: list[str] = field(default_factory=list)  # 출처 URL 목록
    raw_response: dict = field(default_factory=dict)  # 원본 응답
    confidence: float = 0.0  # 결과 신뢰도 (0.0 ~ 1.0)
    latency_ms: int = 0  # 응답 시간
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "provider": self.provider.value,
            "content": self.content,
            "citations": self.citations,
            "confidence": self.confidence,
            "latency_ms": self.latency_ms,
            "timestamp": self.timestamp,
        }


@dataclass
class CrossCoverageResult:
    """
    Cross-Coverage 검색 결과

    Perplexity 실패 필드 → Gemini 커버
    Gemini 실패 필드 → Perplexity 커버
    둘 다 실패 → null
    """
    merged_data: dict  # 필드별 최종 값
    source_map: dict  # 필드별 출처: {"revenue_krw": "PERPLEXITY", "ceo_name": "GEMINI_CROSS_COVERAGE"}
    field_details: list[dict]  # 필드별 상세 정보
    perplexity_success: bool
    gemini_success: bool
    perplexity_citations: list[str] = field(default_factory=list)
    gemini_citations: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "merged_data": self.merged_data,
            "source_map": self.source_map,
            "field_details": self.field_details,
            "perplexity_success": self.perplexity_success,
            "gemini_success": self.gemini_success,
            "perplexity_citations": self.perplexity_citations,
            "gemini_citations": self.gemini_citations,
            "timestamp": self.timestamp,
        }

    @property
    def both_failed(self) -> bool:
        """둘 다 실패했는지 확인"""
        return not self.perplexity_success and not self.gemini_success

    def get_coverage_stats(self) -> dict:
        """커버리지 통계"""
        total = len(self.source_map)
        perplexity_count = sum(1 for s in self.source_map.values() if "PERPLEXITY" in s)
        gemini_count = sum(1 for s in self.source_map.values() if "GEMINI" in s)
        both_failed = sum(1 for s in self.source_map.values() if s == "NONE")

        return {
            "total_fields": total,
            "perplexity_covered": perplexity_count,
            "gemini_covered": gemini_count,
            "both_failed": both_failed,
            "coverage_rate": (total - both_failed) / total if total > 0 else 0.0,
        }


class BaseSearchProvider(ABC):
    """검색 Provider 기본 클래스"""

    provider_type: SearchProviderType

    def __init__(self, circuit_breaker: Optional[CircuitBreakerManager] = None):
        self.circuit_breaker = circuit_breaker or get_circuit_breaker_manager()
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def cleanup(self) -> None:
        """
        P0 Fix: 리소스 정리 - AsyncClient 연결 닫기

        사용 후 반드시 호출하여 TCP 연결 누수 방지
        """
        if self._client is not None:
            try:
                await self._client.aclose()
            except Exception as e:
                logger.warning(f"[SearchProvider] Failed to close client: {e}")
            finally:
                self._client = None

    def __del__(self):
        """소멸자에서 리소스 정리 시도 (best effort)"""
        if self._client is not None:
            try:
                # 동기 컨텍스트에서는 경고만 로깅
                logger.warning(
                    f"[SearchProvider] {self.provider_type.value}: "
                    "AsyncClient not properly closed. Call cleanup() explicitly."
                )
            except Exception:
                pass

    @abstractmethod
    async def search(self, query: str) -> SearchResult:
        """검색 실행 (구현 필수)"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Provider 사용 가능 여부"""
        pass

    async def execute_with_circuit_breaker(self, query: str) -> SearchResult:
        """Circuit Breaker 적용 검색"""
        provider_name = self.provider_type.value

        try:
            # Circuit 상태 확인
            circuit = self.circuit_breaker.get_breaker(provider_name)
            if circuit and not circuit.allow_request():
                raise CircuitOpenError(f"Circuit open for {provider_name}")

            start_time = time.time()
            result = await self.search(query)
            result.latency_ms = int((time.time() - start_time) * 1000)

            # 성공 기록
            if circuit:
                circuit.record_success()

            logger.info(
                f"[SearchProvider] {provider_name} success",
                extra={
                    "provider": provider_name,
                    "latency_ms": result.latency_ms,
                    "citations_count": len(result.citations),
                }
            )

            return result

        except CircuitOpenError:
            raise
        except Exception as e:
            # 실패 기록
            circuit = self.circuit_breaker.get_breaker(provider_name)
            if circuit:
                circuit.record_failure()
            logger.error(f"[SearchProvider] {provider_name} failed: {e}")
            raise


class PerplexityProvider(BaseSearchProvider):
    """Perplexity AI 검색 Provider (Primary)"""

    provider_type = SearchProviderType.PERPLEXITY
    API_URL = "https://api.perplexity.ai/chat/completions"
    MODEL = "sonar-pro"

    def __init__(self, circuit_breaker: Optional[CircuitBreakerManager] = None):
        super().__init__(circuit_breaker)
        self.key_rotator = get_key_rotator()
        self._current_key: Optional[str] = None

    def is_available(self) -> bool:
        # 다중 키 또는 기본 키 중 하나라도 있으면 사용 가능
        key = self.key_rotator.get_key("perplexity")
        return bool(key)

    async def search(self, query: str) -> SearchResult:
        # KeyRotator에서 키 가져오기
        api_key = self.key_rotator.get_key("perplexity")
        if not api_key:
            raise ValueError("Perplexity API key not configured")

        self._current_key = api_key

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that provides accurate, well-sourced information about companies."
                },
                {"role": "user", "content": query}
            ],
            "return_citations": True,
            "return_related_questions": False,
        }

        try:
            response = await self.client.post(
                self.API_URL,
                headers=headers,
                json=payload,
            )
            response.raise_for_status()

            # 성공 시 키 마킹
            self.key_rotator.mark_success("perplexity", api_key)

            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            citations = data.get("citations", [])

            return SearchResult(
                provider=self.provider_type,
                content=content,
                citations=citations,
                raw_response=data,
                confidence=0.9 if citations else 0.7,
            )
        except Exception as e:
            # 실패 시 키 마킹
            self.key_rotator.mark_failed("perplexity", api_key)
            raise


class GeminiGroundingProvider(BaseSearchProvider):
    """Gemini with Google Search Grounding (Fallback 3)"""

    provider_type = SearchProviderType.GEMINI_GROUNDING

    def __init__(self, circuit_breaker: Optional[CircuitBreakerManager] = None):
        super().__init__(circuit_breaker)
        self.key_rotator = get_key_rotator()
        self._current_key: Optional[str] = None

    def is_available(self) -> bool:
        # 다중 키 또는 기본 키 중 하나라도 있으면 사용 가능
        key = self.key_rotator.get_key("google")
        return bool(key)

    async def search(self, query: str) -> SearchResult:
        # KeyRotator에서 키 가져오기
        api_key = self.key_rotator.get_key("google")
        if not api_key:
            raise ValueError("Google API key not configured")

        self._current_key = api_key

        import google.generativeai as genai

        genai.configure(api_key=api_key)

        # Gemini 2.0 Flash with Google Search grounding
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash-exp",
            tools="google_search_retrieval",  # Enable Google Search grounding
        )

        try:
            # P0 Fix: Thread-safe event loop 사용
            loop = _get_or_create_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: model.generate_content(query)
            )

            # 성공 시 키 마킹
            self.key_rotator.mark_success("google", api_key)

            content = response.text if response.text else ""

            # Grounding metadata에서 citations 추출
            citations = []
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'grounding_metadata'):
                    grounding = candidate.grounding_metadata
                    if hasattr(grounding, 'grounding_chunks'):
                        for chunk in grounding.grounding_chunks:
                            if hasattr(chunk, 'web') and hasattr(chunk.web, 'uri'):
                                citations.append(chunk.web.uri)

            return SearchResult(
                provider=self.provider_type,
                content=content,
                citations=citations,
                raw_response={"text": content},
                confidence=0.8 if citations else 0.6,
            )
        except Exception as e:
            # 실패 시 키 마킹
            self.key_rotator.mark_failed("google", api_key)
            raise


class MultiSearchManager:
    """
    Multi-Search Provider Manager

    검색 요청을 우선순위에 따라 여러 Provider에 시도합니다.
    Circuit Breaker와 연동하여 장애 Provider를 자동으로 건너뜁니다.
    """

    def __init__(
        self,
        circuit_breaker: Optional[CircuitBreakerManager] = None,
        providers: Optional[list[BaseSearchProvider]] = None,
    ):
        self.circuit_breaker = circuit_breaker or get_circuit_breaker_manager()

        # 검색 내장 LLM 2-Track (Perplexity + Gemini Grounding)
        if providers:
            self.providers = providers
        else:
            self.providers = [
                PerplexityProvider(self.circuit_breaker),      # Primary - 실시간 검색 + AI 요약
                GeminiGroundingProvider(self.circuit_breaker), # Fallback - Google Search 기반
            ]

    def get_available_providers(self) -> list[BaseSearchProvider]:
        """사용 가능한 Provider 목록"""
        return [p for p in self.providers if p.is_available()]

    async def cleanup(self) -> None:
        """
        P0 Fix: 모든 Provider 리소스 정리

        사용 후 반드시 호출하여 TCP 연결 누수 방지.
        개별 Provider cleanup 실패는 로깅 후 계속 진행.
        """
        for provider in self.providers:
            try:
                await provider.cleanup()
            except Exception as e:
                logger.warning(
                    f"[MultiSearchManager] Failed to cleanup {provider.provider_type.value}: {e}"
                )

    async def search(
        self,
        query: str,
        preferred_provider: Optional[SearchProviderType] = None,
    ) -> SearchResult:
        """
        멀티 Provider 검색 실행

        Args:
            query: 검색 쿼리
            preferred_provider: 선호 Provider (지정 시 해당 Provider 우선 시도)

        Returns:
            SearchResult: 첫 번째 성공한 Provider의 결과

        Raises:
            AllProvidersFailedError: 모든 Provider 실패
        """
        from app.worker.llm.exceptions import AllProvidersFailedError

        available = self.get_available_providers()

        if not available:
            raise AllProvidersFailedError("No search providers available")

        # 선호 Provider가 있으면 순서 조정
        if preferred_provider:
            available = sorted(
                available,
                key=lambda p: 0 if p.provider_type == preferred_provider else 1
            )

        errors = []

        for provider in available:
            try:
                logger.info(f"[MultiSearch] Trying {provider.provider_type.value}")
                result = await provider.execute_with_circuit_breaker(query)

                logger.info(
                    f"[MultiSearch] Success with {provider.provider_type.value}",
                    extra={
                        "provider": provider.provider_type.value,
                        "latency_ms": result.latency_ms,
                        "confidence": result.confidence,
                    }
                )

                return result

            except CircuitOpenError as e:
                logger.warning(f"[MultiSearch] Circuit open for {provider.provider_type.value}")
                errors.append(f"{provider.provider_type.value}: Circuit open")
                continue

            except Exception as e:
                logger.warning(f"[MultiSearch] {provider.provider_type.value} failed: {e}")
                errors.append(f"{provider.provider_type.value}: {str(e)}")
                continue

        raise AllProvidersFailedError(
            f"All search providers failed: {'; '.join(errors)}"
        )

    async def search_parallel(
        self,
        query: str,
        max_providers: int = 2,
    ) -> list[SearchResult]:
        """
        병렬 검색 (다중 소스 크로스 체크용)

        Args:
            query: 검색 쿼리
            max_providers: 병렬 시도할 최대 Provider 수

        Returns:
            list[SearchResult]: 성공한 모든 Provider의 결과
        """
        available = self.get_available_providers()[:max_providers]

        if not available:
            return []

        tasks = [
            provider.execute_with_circuit_breaker(query)
            for provider in available
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        successful = []
        for i, result in enumerate(results):
            if isinstance(result, SearchResult):
                successful.append(result)
            else:
                logger.warning(
                    f"[MultiSearch Parallel] {available[i].provider_type.value} failed: {result}"
                )

        return successful

    async def search_with_cross_coverage(
        self,
        query: str,
        fields: list[str],
    ) -> CrossCoverageResult:
        """
        Cross-Coverage 검색

        로직:
        1. Perplexity + Gemini 병렬 검색
        2. 필드별로 결과 비교
        3. Perplexity 실패 필드 → Gemini 값 사용
        4. Gemini 실패 필드 → Perplexity 값 사용
        5. 둘 다 실패 → null

        Args:
            query: 검색 쿼리
            fields: 추출할 필드 목록

        Returns:
            CrossCoverageResult: 필드별 결과 및 소스 정보
        """
        from app.worker.llm.field_assignment import (
            get_field_confidence_weight,
            get_source_credibility,
            requires_cross_validation,
        )

        # 병렬 검색 실행
        results = await self.search_parallel(query, max_providers=2)

        perplexity_result = None
        gemini_result = None

        for result in results:
            if result.provider == SearchProviderType.PERPLEXITY:
                perplexity_result = result
            elif result.provider == SearchProviderType.GEMINI_GROUNDING:
                gemini_result = result

        # 필드별 Cross-Coverage 적용
        merged_data = {}
        source_map = {}
        field_details = []

        for field_name in fields:
            p_value = None
            g_value = None
            p_source = None
            g_source = None

            # Perplexity 결과에서 필드 추출
            if perplexity_result and perplexity_result.raw_response:
                p_value = self._extract_field_from_response(
                    perplexity_result.raw_response, field_name
                )
                if perplexity_result.citations:
                    p_source = perplexity_result.citations[0] if perplexity_result.citations else None

            # Gemini 결과에서 필드 추출
            if gemini_result and gemini_result.raw_response:
                g_value = self._extract_field_from_response(
                    gemini_result.raw_response, field_name
                )
                if gemini_result.citations:
                    g_source = gemini_result.citations[0] if gemini_result.citations else None

            # Cross-Coverage 로직 적용
            final_value = None
            final_source = None
            coverage_type = "NONE"

            if p_value is not None and g_value is not None:
                # 둘 다 있음 → 신뢰도 기반 선택
                if requires_cross_validation(field_name):
                    # Cross-Validation 필수 필드: 출처 신뢰도로 선택
                    p_score = get_source_credibility(p_source) * get_field_confidence_weight(field_name, "perplexity")
                    g_score = get_source_credibility(g_source) * get_field_confidence_weight(field_name, "gemini")

                    if p_score >= g_score:
                        final_value = p_value
                        final_source = "PERPLEXITY"
                    else:
                        final_value = g_value
                        final_source = "GEMINI"
                    coverage_type = "CROSS_VALIDATED"
                else:
                    # 일반 필드: Perplexity 우선
                    final_value = p_value
                    final_source = "PERPLEXITY"
                    coverage_type = "PERPLEXITY_PRIMARY"

            elif p_value is not None:
                # Perplexity만 성공
                final_value = p_value
                final_source = "PERPLEXITY"
                coverage_type = "PERPLEXITY_ONLY"

            elif g_value is not None:
                # Gemini만 성공 (Perplexity 실패 커버)
                final_value = g_value
                final_source = "GEMINI_CROSS_COVERAGE"
                coverage_type = "GEMINI_COVERAGE"

            else:
                # 둘 다 실패 → null
                final_value = None
                final_source = "NONE"
                coverage_type = "BOTH_FAILED"

            merged_data[field_name] = final_value
            source_map[field_name] = final_source

            field_details.append({
                "field": field_name,
                "value": final_value,
                "source": final_source,
                "coverage_type": coverage_type,
                "perplexity_value": p_value,
                "gemini_value": g_value,
            })

        return CrossCoverageResult(
            merged_data=merged_data,
            source_map=source_map,
            field_details=field_details,
            perplexity_success=perplexity_result is not None,
            gemini_success=gemini_result is not None,
            perplexity_citations=perplexity_result.citations if perplexity_result else [],
            gemini_citations=gemini_result.citations if gemini_result else [],
        )

    def _extract_field_from_response(self, response: dict, field_name: str) -> Any:
        """응답에서 특정 필드 추출 (JSON 파싱 시도)"""
        # content 필드에서 JSON 추출 시도
        content = response.get("content") or response.get("text", "")
        if not content:
            return None

        # JSON 블록 추출 시도
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', content)
        if json_match:
            try:
                parsed = json.loads(json_match.group(1))
                return parsed.get(field_name)
            except json.JSONDecodeError:
                pass

        # 직접 JSON 파싱 시도
        try:
            parsed = json.loads(content)
            return parsed.get(field_name)
        except json.JSONDecodeError:
            pass

        return None


# ============================================================
# Singleton & Factory
# ============================================================

_multi_search_manager: Optional[MultiSearchManager] = None


def get_multi_search_manager() -> MultiSearchManager:
    """MultiSearchManager 싱글톤"""
    global _multi_search_manager
    if _multi_search_manager is None:
        _multi_search_manager = MultiSearchManager()
    return _multi_search_manager


async def reset_multi_search_manager() -> None:
    """
    싱글톤 리셋 (테스트용)

    P0 Fix: 리셋 전 리소스 정리
    """
    global _multi_search_manager
    if _multi_search_manager is not None:
        try:
            await _multi_search_manager.cleanup()
        except Exception as e:
            logger.warning(f"[MultiSearchManager] Failed to cleanup before reset: {e}")
    _multi_search_manager = None


# ============================================================
# Provider 상태 조회 API 헬퍼
# ============================================================

def get_search_providers_status() -> dict:
    """모든 검색 Provider 상태 조회"""
    manager = get_multi_search_manager()
    cb_manager = get_circuit_breaker_manager()

    status = {}
    for provider in manager.providers:
        provider_name = provider.provider_type.value
        circuit = cb_manager.get_breaker(provider_name)

        status[provider_name] = {
            "available": provider.is_available(),
            "circuit_state": circuit.state.value if circuit else "unknown",
            "failure_count": circuit.failure_count if circuit else 0,
        }

    return status
