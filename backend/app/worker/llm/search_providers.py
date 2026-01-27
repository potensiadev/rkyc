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
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Any

import httpx

from app.core.config import settings
from app.worker.llm.circuit_breaker import (
    CircuitBreakerManager,
    CircuitOpenError,
    get_circuit_breaker_manager,
)

logger = logging.getLogger(__name__)


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
            circuit = self.circuit_breaker.get_circuit(provider_name)
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
            circuit = self.circuit_breaker.get_circuit(provider_name)
            if circuit:
                circuit.record_failure()
            logger.error(f"[SearchProvider] {provider_name} failed: {e}")
            raise


class PerplexityProvider(BaseSearchProvider):
    """Perplexity AI 검색 Provider (Primary)"""

    provider_type = SearchProviderType.PERPLEXITY
    API_URL = "https://api.perplexity.ai/chat/completions"
    MODEL = "sonar-pro"

    def is_available(self) -> bool:
        return bool(settings.PERPLEXITY_API_KEY)

    async def search(self, query: str) -> SearchResult:
        if not self.is_available():
            raise ValueError("Perplexity API key not configured")

        headers = {
            "Authorization": f"Bearer {settings.PERPLEXITY_API_KEY}",
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

        response = await self.client.post(
            self.API_URL,
            headers=headers,
            json=payload,
        )
        response.raise_for_status()

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


class GeminiGroundingProvider(BaseSearchProvider):
    """Gemini with Google Search Grounding (Fallback 3)"""

    provider_type = SearchProviderType.GEMINI_GROUNDING

    def is_available(self) -> bool:
        return bool(settings.GOOGLE_API_KEY)

    async def search(self, query: str) -> SearchResult:
        if not self.is_available():
            raise ValueError("Google API key not configured")

        import google.generativeai as genai

        genai.configure(api_key=settings.GOOGLE_API_KEY)

        # Gemini 2.0 Flash with Google Search grounding
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash-exp",
            tools="google_search_retrieval",  # Enable Google Search grounding
        )

        # Sync call wrapped in asyncio
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: model.generate_content(query)
        )

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


def reset_multi_search_manager() -> None:
    """싱글톤 리셋 (테스트용)"""
    global _multi_search_manager
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
        circuit = cb_manager.get_circuit(provider_name)

        status[provider_name] = {
            "available": provider.is_available(),
            "circuit_state": circuit.state.value if circuit else "unknown",
            "failure_count": circuit.failure_count if circuit else 0,
        }

    return status
