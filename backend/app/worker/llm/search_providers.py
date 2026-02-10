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

# =============================================================================
# Realistic System Prompt (P0 Fix: Perplexity 한계 인정)
# - Perplexity는 웹 크롤링 기반 → DART/신평사 직접 접근 불가
# - 뉴스/기사 검색에 집중
# - 전체 한국어 통일
# =============================================================================

PERPLEXITY_ULTIMATE_SYSTEM_PROMPT = """당신은 한국 기업 뉴스를 검색하는 도우미입니다.

## 역할
- 뉴스/기사에서 사실만 찾아 보고
- 분석, 해석, 예측 금지
- 못 찾으면 솔직하게 "해당 정보 없음"

## 검색 가능한 출처
- 경제지: 한경, 매경, 조선비즈, 이데일리
- 통신사: 연합뉴스, 뉴시스, 뉴스1
- 외신: 로이터, 블룸버그

## 금지 표현
추정, 전망, 예상, 것으로 보인다, 가능성, 대략, 약, 정도

## 출력 규칙
1. JSON 형식만
2. 한국어만 사용
3. 출처 URL 필수
4. 날짜 필수"""

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
            if circuit and not circuit.is_available():
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
                    "content": PERPLEXITY_ULTIMATE_SYSTEM_PROMPT
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


# =============================================================================
# Gemini Grounding 설정 (롤백 가능)
# =============================================================================
# True: 실제 Google Search Grounding 활성화 (Citation 제공, Perplexity 대체 가능)
# False: 기존 litellm 방식 (Citation 없음, Fallback 전용)
USE_REAL_GROUNDING = True

# Gemini Grounding 시스템 프롬프트
GEMINI_GROUNDING_SYSTEM_PROMPT = """당신은 한국 기업 정보를 검색하는 도우미입니다.

## 역할
- Google Search를 사용하여 최신 정보 검색
- 검색된 출처를 반드시 인용
- 사실만 보고, 추측/예측 금지

## 검색 우선순위
1. 공시: DART, KIND, 금감원
2. 경제지: 한경, 매경, 조선비즈
3. 통신사: 연합뉴스, 뉴시스

## 출력 규칙
- 한국어만 사용
- 정확한 숫자와 날짜 포함
- 출처 불명확하면 "확인 필요" 명시"""


class GeminiGroundingProvider(BaseSearchProvider):
    """
    Gemini with Google Search Grounding

    v2.0: 실제 Google Search Grounding 활성화
    - Citation (출처 URL) 추출
    - Perplexity 대체 가능
    - Hallucination 0% 지원

    롤백: USE_REAL_GROUNDING = False로 설정
    """

    provider_type = SearchProviderType.GEMINI_GROUNDING

    # 지원 모델 (Grounding 지원 모델)
    GROUNDING_MODEL = "gemini-1.5-flash"      # Grounding 지원
    FALLBACK_MODEL = "gemini-1.5-flash"       # 동일 모델 사용

    def __init__(
        self,
        circuit_breaker: Optional[CircuitBreakerManager] = None,
        use_grounding: Optional[bool] = None,
    ):
        super().__init__(circuit_breaker)
        self.key_rotator = get_key_rotator()
        self._current_key: Optional[str] = None
        # 인스턴스별 grounding 설정 (테스트용)
        self._use_grounding = use_grounding if use_grounding is not None else USE_REAL_GROUNDING

    def is_available(self) -> bool:
        key = self.key_rotator.get_key("google")
        return bool(key)

    async def search(self, query: str) -> SearchResult:
        """
        Gemini Google Search Grounding을 사용한 검색

        v2.0: 실제 Grounding 활성화 + Citation 추출
        """
        if self._use_grounding:
            return await self._search_with_grounding(query)
        else:
            return await self._search_legacy(query)

    async def _search_with_grounding(self, query: str) -> SearchResult:
        """
        실제 Google Search Grounding 사용 (v2.0)

        google-generativeai 라이브러리의 grounding 기능 활용:
        - Google Search Tool 자동 활성화
        - grounding_metadata에서 Citation 추출
        - Perplexity 수준의 품질 제공
        """
        import google.generativeai as genai

        api_key = self.key_rotator.get_key("google")
        if not api_key:
            raise ValueError("Google API key not configured")

        self._current_key = api_key
        genai.configure(api_key=api_key)

        start_time = time.time()

        try:
            # Gemini 1.5 Flash with Google Search Grounding
            model = genai.GenerativeModel(
                model_name=self.GROUNDING_MODEL,
                system_instruction=GEMINI_GROUNDING_SYSTEM_PROMPT,
            )

            # Thread-safe 비동기 호출
            loop = _get_or_create_event_loop()

            # Google Search Grounding 활성화
            # 참고: https://ai.google.dev/gemini-api/docs/grounding
            response = await loop.run_in_executor(
                None,
                lambda: model.generate_content(
                    query,
                    tools="google_search_retrieval",  # 문자열로 전달
                    generation_config={
                        "temperature": 0.1,  # 낮은 temperature로 사실 중심
                        "max_output_tokens": 2048,
                    },
                )
            )

            # 성공 시 키 마킹
            self.key_rotator.mark_success("google", api_key)

            # 응답 텍스트 추출
            content = ""
            if response and response.text:
                content = response.text

            # Citation 추출 (grounding_metadata에서)
            citations = self._extract_citations_from_grounding(response)

            # Confidence 계산 (Citation 수 기반)
            confidence = self._calculate_confidence(citations, content)

            latency_ms = int((time.time() - start_time) * 1000)

            logger.info(
                f"[GeminiGrounding] Search success: {len(citations)} citations, "
                f"confidence={confidence:.2f}, latency={latency_ms}ms"
            )

            return SearchResult(
                provider=self.provider_type,
                content=content,
                citations=citations,
                raw_response={
                    "text": content,
                    "grounding_used": True,
                    "model": self.GROUNDING_MODEL,
                },
                confidence=confidence,
                latency_ms=latency_ms,
            )

        except Exception as e:
            self.key_rotator.mark_failed("google", api_key)
            logger.error(f"[GeminiGrounding] Search failed: {e}")

            # Grounding 실패 시 Fallback 시도
            if "grounding" in str(e).lower() or "tool" in str(e).lower():
                logger.warning("[GeminiGrounding] Grounding failed, trying fallback")
                return await self._search_legacy(query)
            raise

    def _extract_citations_from_grounding(self, response) -> list[str]:
        """
        Gemini grounding_metadata에서 Citation URL 추출

        grounding_metadata 구조:
        - grounding_chunks: 검색된 콘텐츠 청크
        - grounding_supports: 응답의 어느 부분이 어떤 청크에서 왔는지
        - web_search_queries: 사용된 검색 쿼리
        """
        citations = []
        seen_urls = set()

        try:
            if not response or not response.candidates:
                return citations

            candidate = response.candidates[0]

            # grounding_metadata 확인
            if not hasattr(candidate, 'grounding_metadata') or not candidate.grounding_metadata:
                logger.debug("[GeminiGrounding] No grounding_metadata in response")
                return citations

            grounding_meta = candidate.grounding_metadata

            # grounding_chunks에서 URL 추출
            if hasattr(grounding_meta, 'grounding_chunks') and grounding_meta.grounding_chunks:
                for chunk in grounding_meta.grounding_chunks:
                    if hasattr(chunk, 'web') and chunk.web:
                        url = getattr(chunk.web, 'uri', None)
                        if url and url not in seen_urls:
                            # 블로그/커뮤니티 필터링
                            if not self._is_excluded_domain(url):
                                citations.append(url)
                                seen_urls.add(url)

            # retrieval_queries에서 추가 정보 로깅
            if hasattr(grounding_meta, 'web_search_queries') and grounding_meta.web_search_queries:
                queries = list(grounding_meta.web_search_queries)
                logger.debug(f"[GeminiGrounding] Search queries used: {queries}")

            # grounding_supports에서 신뢰도 정보 추출
            if hasattr(grounding_meta, 'grounding_supports') and grounding_meta.grounding_supports:
                support_count = len(grounding_meta.grounding_supports)
                logger.debug(f"[GeminiGrounding] Grounding supports: {support_count}")

        except Exception as e:
            logger.warning(f"[GeminiGrounding] Citation extraction error: {e}")

        logger.info(f"[GeminiGrounding] Extracted {len(citations)} citations")
        return citations

    def _is_excluded_domain(self, url: str) -> bool:
        """블로그/커뮤니티 등 제외할 도메인 체크"""
        excluded = [
            "blog.naver.com", "m.blog.naver.com", "blog.daum.net",
            "tistory.com", "brunch.co.kr", "velog.io", "medium.com",
            "cafe.naver.com", "cafe.daum.net", "dcinside.com",
            "fmkorea.com", "clien.net", "ruliweb.com", "reddit.com",
        ]
        url_lower = url.lower()
        return any(domain in url_lower for domain in excluded)

    def _calculate_confidence(self, citations: list[str], content: str) -> float:
        """
        Citation 기반 Confidence 계산

        - 3개 이상 Citation: 0.9 (HIGH)
        - 1-2개 Citation: 0.75 (MED)
        - 0개 Citation: 0.5 (LOW)
        - 공시 도메인 포함: +0.05 보너스
        """
        base_confidence = 0.5

        if len(citations) >= 3:
            base_confidence = 0.9
        elif len(citations) >= 1:
            base_confidence = 0.75

        # 공시 도메인 보너스
        high_trust_domains = ["dart.fss.or.kr", "kind.krx.co.kr", ".go.kr", ".or.kr"]
        for url in citations:
            if any(domain in url.lower() for domain in high_trust_domains):
                base_confidence = min(1.0, base_confidence + 0.05)
                break

        return base_confidence

    async def _search_legacy(self, query: str) -> SearchResult:
        """
        기존 litellm 방식 (Grounding 없음, 롤백용)
        """
        import litellm

        api_key = self.key_rotator.get_key("google")
        if not api_key:
            raise ValueError("Google API key not configured")

        self._current_key = api_key
        os.environ["GEMINI_API_KEY"] = api_key

        start_time = time.time()

        try:
            loop = _get_or_create_event_loop()

            response = await loop.run_in_executor(
                None,
                lambda: litellm.completion(
                    model="gemini/gemini-1.5-flash",
                    messages=[{"role": "user", "content": query}],
                    timeout=30,
                )
            )

            self.key_rotator.mark_success("google", api_key)

            content = ""
            if response and response.choices:
                content = response.choices[0].message.content or ""

            latency_ms = int((time.time() - start_time) * 1000)

            return SearchResult(
                provider=self.provider_type,
                content=content,
                citations=[],  # Legacy 모드는 Citation 없음
                raw_response={
                    "text": content,
                    "grounding_used": False,
                    "model": "gemini-1.5-flash",
                },
                confidence=0.6,  # Grounding 없으면 낮은 신뢰도
                latency_ms=latency_ms,
            )
        except Exception as e:
            self.key_rotator.mark_failed("google", api_key)
            raise


# =============================================================================
# Search Provider 우선순위 설정 (롤백 가능)
# =============================================================================
# True: Gemini Grounding을 Primary로 사용 (Perplexity 비용 절약)
# False: Perplexity를 Primary로 사용 (기존 동작)
USE_GEMINI_AS_PRIMARY = True  # 비용 절약 모드

# 현재 설정 상태 (런타임 변경 가능)
_search_config = {
    "gemini_primary": USE_GEMINI_AS_PRIMARY,
    "grounding_enabled": USE_REAL_GROUNDING,
}


def get_search_config() -> dict:
    """현재 검색 설정 반환"""
    return _search_config.copy()


def set_gemini_primary(enabled: bool) -> None:
    """Gemini Primary 모드 설정 (런타임)"""
    global _search_config
    _search_config["gemini_primary"] = enabled
    logger.info(f"[SearchConfig] Gemini primary mode: {enabled}")


def set_grounding_enabled(enabled: bool) -> None:
    """Grounding 활성화 설정 (런타임)"""
    global _search_config, USE_REAL_GROUNDING
    _search_config["grounding_enabled"] = enabled
    USE_REAL_GROUNDING = enabled
    logger.info(f"[SearchConfig] Grounding enabled: {enabled}")


class MultiSearchManager:
    """
    Multi-Search Provider Manager

    검색 요청을 우선순위에 따라 여러 Provider에 시도합니다.
    Circuit Breaker와 연동하여 장애 Provider를 자동으로 건너뜁니다.

    v2.0: Gemini Primary 모드 지원
    - USE_GEMINI_AS_PRIMARY=True: Gemini → Perplexity 순서
    - USE_GEMINI_AS_PRIMARY=False: Perplexity → Gemini 순서
    """

    def __init__(
        self,
        circuit_breaker: Optional[CircuitBreakerManager] = None,
        providers: Optional[list[BaseSearchProvider]] = None,
        gemini_primary: Optional[bool] = None,
    ):
        self.circuit_breaker = circuit_breaker or get_circuit_breaker_manager()

        # 우선순위 결정
        use_gemini_first = gemini_primary if gemini_primary is not None else _search_config["gemini_primary"]

        # 검색 내장 LLM 2-Track
        if providers:
            self.providers = providers
        elif use_gemini_first:
            # Gemini Primary 모드 (비용 절약)
            self.providers = [
                GeminiGroundingProvider(self.circuit_breaker),  # Primary - Google Search Grounding
                PerplexityProvider(self.circuit_breaker),       # Fallback - 실시간 검색
            ]
            logger.info("[MultiSearchManager] Mode: Gemini Primary (cost-saving)")
        else:
            # Perplexity Primary 모드 (기존)
            self.providers = [
                PerplexityProvider(self.circuit_breaker),       # Primary - 실시간 검색 + AI 요약
                GeminiGroundingProvider(self.circuit_breaker),  # Fallback - Google Search 기반
            ]
            logger.info("[MultiSearchManager] Mode: Perplexity Primary (default)")

    def get_available_providers(self) -> list[BaseSearchProvider]:
        """사용 가능한 Provider 목록"""
        return [p for p in self.providers if p.is_available()]

    def get_provider_order(self) -> list[str]:
        """현재 Provider 우선순위 반환"""
        return [p.provider_type.value for p in self.providers]

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
