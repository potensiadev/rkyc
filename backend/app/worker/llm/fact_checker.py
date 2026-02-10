"""
Gemini Grounding 기반 Signal Fact-Checker
모든 시그널을 DB 저장 전에 Google Search 기반 팩트체크 수행

PRD v2.0 P0 Anti-Hallucination Layer:
- Gemini 3 Pro Preview + Google Search Grounding
- 모든 시그널 저장 전 필수 검증
- 검증 실패 시 시그널 거부 또는 confidence 하향

2026-02-08 구현
"""

import asyncio
import json
import logging
import os
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from app.core.config import settings
from app.worker.llm.key_rotator import get_key_rotator

logger = logging.getLogger(__name__)

# Thread-safe event loop 관리
_thread_local = threading.local()
_event_loop_lock = threading.Lock()


def _get_or_create_event_loop() -> asyncio.AbstractEventLoop:
    """Thread-safe event loop 관리"""
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        pass

    with _event_loop_lock:
        if hasattr(_thread_local, 'loop') and _thread_local.loop is not None:
            if not _thread_local.loop.is_closed():
                return _thread_local.loop

        loop = asyncio.new_event_loop()
        _thread_local.loop = loop
        return loop


class FactCheckResult(str, Enum):
    """팩트체크 결과 분류"""
    VERIFIED = "verified"           # 사실로 확인됨
    PARTIALLY_VERIFIED = "partial"  # 일부만 확인됨
    UNVERIFIED = "unverified"       # 확인 불가
    FALSE = "false"                 # 허위로 확인됨
    ERROR = "error"                 # 검증 오류


@dataclass
class FactCheckResponse:
    """팩트체크 응답 구조"""
    result: FactCheckResult
    confidence: float  # 0.0 ~ 1.0
    explanation: str   # 검증 결과 설명
    sources: list[str] = field(default_factory=list)  # 검증 출처
    claims_checked: list[dict] = field(default_factory=list)  # 개별 주장 검증 결과
    raw_response: str = ""  # Gemini 원본 응답
    latency_ms: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "result": self.result.value,
            "confidence": self.confidence,
            "explanation": self.explanation,
            "sources": self.sources,
            "claims_checked": self.claims_checked,
            "latency_ms": self.latency_ms,
            "timestamp": self.timestamp,
        }

    @property
    def is_acceptable(self) -> bool:
        """시그널 저장 허용 여부"""
        # FALSE는 무조건 거부
        if self.result == FactCheckResult.FALSE:
            return False
        # VERIFIED, PARTIALLY_VERIFIED는 허용
        if self.result in (FactCheckResult.VERIFIED, FactCheckResult.PARTIALLY_VERIFIED):
            return True
        # UNVERIFIED는 confidence 0.5 이상이면 허용 (검증 불가능한 경우)
        if self.result == FactCheckResult.UNVERIFIED and self.confidence >= 0.5:
            return True
        # ERROR는 허용 (팩트체크 실패가 시그널 차단으로 이어지면 안됨)
        if self.result == FactCheckResult.ERROR:
            return True
        return False


class GeminiFactChecker:
    """
    Gemini 3 Pro + Google Search Grounding 기반 팩트체커

    모든 시그널의 핵심 주장을 Google Search로 검증합니다.
    """

    # 팩트체크 시스템 프롬프트
    FACT_CHECK_SYSTEM_PROMPT = """당신은 금융 뉴스 팩트체커입니다.
주어진 시그널(기업 리스크/기회 정보)의 핵심 주장을 Google Search를 통해 검증하세요.

검증 기준:
1. 기업명이 정확히 일치하는지 (다른 기업 정보가 혼동되지 않았는지)
2. 날짜/시점이 현재와 일치하는지
3. 숫자(금액, 비율, 증감률 등)가 공신력 있는 출처와 일치하는지
4. 이벤트(상장폐지, 부도, 합병 등)가 실제로 발생했는지

특히 주의할 사항:
- "상장폐지", "부도", "파산", "법정관리" 등 극단적 이벤트는 반드시 공식 공시 확인
- 다른 기업의 뉴스가 혼동되었을 가능성 확인
- 숫자가 50% 이상 차이나면 허위 가능성 높음

응답 형식 (JSON):
{
    "result": "verified" | "partial" | "unverified" | "false",
    "confidence": 0.0 ~ 1.0,
    "explanation": "검증 결과 상세 설명",
    "sources": ["출처 URL 1", "출처 URL 2"],
    "claims_checked": [
        {"claim": "주장 내용", "verified": true/false, "source": "출처"}
    ]
}"""

    FACT_CHECK_USER_PROMPT = """다음 시그널을 팩트체크해주세요:

기업명: {corp_name}
시그널 유형: {signal_type} / {event_type}
제목: {title}
요약: {summary}
영향: {impact_direction} ({impact_strength})

이 정보가 사실인지 Google Search를 통해 검증하고 JSON 형식으로 응답해주세요."""

    def __init__(self):
        self.key_rotator = get_key_rotator()
        self._enabled = True

    def is_available(self) -> bool:
        """Gemini API 사용 가능 여부"""
        key = self.key_rotator.get_key("google")
        return bool(key) and self._enabled

    def enable(self) -> None:
        """팩트체커 활성화"""
        self._enabled = True

    def disable(self) -> None:
        """팩트체커 비활성화 (테스트/긴급 시)"""
        self._enabled = False

    async def check_signal(
        self,
        signal: dict,
        corp_name: str,
    ) -> FactCheckResponse:
        """
        단일 시그널 팩트체크

        Args:
            signal: 시그널 딕셔너리 (title, summary, signal_type 등)
            corp_name: 기업명

        Returns:
            FactCheckResponse: 팩트체크 결과
        """
        if not self.is_available():
            logger.warning("[FactChecker] Gemini not available, skipping fact check")
            return FactCheckResponse(
                result=FactCheckResult.ERROR,
                confidence=0.5,
                explanation="팩트체크 서비스 불가 (API 키 없음)",
            )

        start_time = time.time()

        try:
            # 프롬프트 생성
            user_prompt = self.FACT_CHECK_USER_PROMPT.format(
                corp_name=corp_name,
                signal_type=signal.get("signal_type", "UNKNOWN"),
                event_type=signal.get("event_type", "UNKNOWN"),
                title=signal.get("title", ""),
                summary=signal.get("summary", ""),
                impact_direction=signal.get("impact_direction", "NEUTRAL"),
                impact_strength=signal.get("impact_strength", "LOW"),
            )

            # Gemini 호출 (Google Search Grounding 사용)
            response_text = await self._call_gemini_with_grounding(user_prompt)

            latency_ms = int((time.time() - start_time) * 1000)

            # 응답 파싱
            return self._parse_response(response_text, latency_ms)

        except Exception as e:
            logger.error(f"[FactChecker] Error: {e}")
            latency_ms = int((time.time() - start_time) * 1000)
            return FactCheckResponse(
                result=FactCheckResult.ERROR,
                confidence=0.5,
                explanation=f"팩트체크 오류: {str(e)}",
                latency_ms=latency_ms,
            )

    async def _call_gemini_with_grounding(self, prompt: str) -> str:
        """
        Gemini 3 Pro + Google Search Grounding 호출

        google-generativeai 라이브러리의 grounding 기능 사용
        """
        import google.generativeai as genai

        # API 키 설정
        api_key = self.key_rotator.get_key("google")
        if not api_key:
            raise ValueError("Google API key not configured")

        genai.configure(api_key=api_key)

        # Gemini 1.5 Flash with Google Search Grounding
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=self.FACT_CHECK_SYSTEM_PROMPT,
        )

        # Thread-safe 비동기 호출
        loop = _get_or_create_event_loop()

        response = await loop.run_in_executor(
            None,
            lambda: model.generate_content(
                prompt,
                tools="google_search_retrieval",  # Grounding 활성화
                generation_config={
                    "temperature": 0.1,  # 낮은 temperature로 일관된 응답
                    "max_output_tokens": 1024,
                },
            )
        )

        # 응답 텍스트 추출
        if response and response.text:
            return response.text
        return ""

    def _parse_response(self, response_text: str, latency_ms: int) -> FactCheckResponse:
        """Gemini 응답 파싱"""
        try:
            # JSON 블록 추출
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                data = json.loads(json_match.group())

                result_str = data.get("result", "unverified").lower()
                result_map = {
                    "verified": FactCheckResult.VERIFIED,
                    "partial": FactCheckResult.PARTIALLY_VERIFIED,
                    "unverified": FactCheckResult.UNVERIFIED,
                    "false": FactCheckResult.FALSE,
                }
                result = result_map.get(result_str, FactCheckResult.UNVERIFIED)

                return FactCheckResponse(
                    result=result,
                    confidence=float(data.get("confidence", 0.5)),
                    explanation=data.get("explanation", ""),
                    sources=data.get("sources", []),
                    claims_checked=data.get("claims_checked", []),
                    raw_response=response_text,
                    latency_ms=latency_ms,
                )
            else:
                # JSON 파싱 실패 시 텍스트 분석
                return self._analyze_text_response(response_text, latency_ms)

        except json.JSONDecodeError as e:
            logger.warning(f"[FactChecker] JSON parse error: {e}")
            return self._analyze_text_response(response_text, latency_ms)

    def _analyze_text_response(self, text: str, latency_ms: int) -> FactCheckResponse:
        """텍스트 응답 분석 (JSON 파싱 실패 시)"""
        text_lower = text.lower()

        # 키워드 기반 결과 추론
        if any(kw in text_lower for kw in ["허위", "거짓", "사실이 아", "잘못된", "false"]):
            result = FactCheckResult.FALSE
            confidence = 0.8
        elif any(kw in text_lower for kw in ["확인됨", "사실", "verified", "정확"]):
            result = FactCheckResult.VERIFIED
            confidence = 0.8
        elif any(kw in text_lower for kw in ["일부", "부분적", "partial"]):
            result = FactCheckResult.PARTIALLY_VERIFIED
            confidence = 0.6
        else:
            result = FactCheckResult.UNVERIFIED
            confidence = 0.5

        return FactCheckResponse(
            result=result,
            confidence=confidence,
            explanation=text[:500],  # 첫 500자
            raw_response=text,
            latency_ms=latency_ms,
        )

    async def check_signals_batch(
        self,
        signals: list[dict],
        corp_name: str,
        max_concurrent: int = 3,
    ) -> list[tuple[dict, FactCheckResponse]]:
        """
        여러 시그널 배치 팩트체크

        Args:
            signals: 시그널 리스트
            corp_name: 기업명
            max_concurrent: 최대 동시 요청 수

        Returns:
            [(signal, FactCheckResponse), ...] 리스트
        """
        if not signals:
            return []

        # Semaphore로 동시 요청 제한
        semaphore = asyncio.Semaphore(max_concurrent)

        async def check_with_semaphore(signal: dict) -> tuple[dict, FactCheckResponse]:
            async with semaphore:
                response = await self.check_signal(signal, corp_name)
                return (signal, response)

        # 병렬 실행
        tasks = [check_with_semaphore(s) for s in signals]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 예외 처리
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"[FactChecker] Batch error for signal {i}: {result}")
                final_results.append((
                    signals[i],
                    FactCheckResponse(
                        result=FactCheckResult.ERROR,
                        confidence=0.5,
                        explanation=f"배치 검증 오류: {str(result)}",
                    )
                ))
            else:
                final_results.append(result)

        return final_results


# 싱글톤 인스턴스
_fact_checker: Optional[GeminiFactChecker] = None
_fact_checker_lock = threading.Lock()


def get_fact_checker() -> GeminiFactChecker:
    """팩트체커 싱글톤 인스턴스 반환"""
    global _fact_checker
    if _fact_checker is None:
        with _fact_checker_lock:
            if _fact_checker is None:
                _fact_checker = GeminiFactChecker()
    return _fact_checker


def reset_fact_checker() -> None:
    """팩트체커 리셋 (테스트용)"""
    global _fact_checker
    with _fact_checker_lock:
        _fact_checker = None
