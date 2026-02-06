"""
External LLM Service
보안 아키텍처: 외부 공개 데이터 전용 LLM

✅ 허용 작업:
- 공개 뉴스/기사 수집 및 요약
- DART 공시 정보 분석
- 정책/규제 변화 모니터링
- 산업 동향 분석
- 외부 이벤트 → 시그널 초안 생성

❌ 금지 작업:
- 특정 법인 고객 정보 처리
- 내부 여신/담보 정보 분석
- 고객 거래 내역 처리
- 내부 신용등급 관련 분석
"""

import json
import hashlib
import logging
from datetime import datetime
from typing import Optional

import httpx
import litellm
from litellm import completion

from app.core.config import settings
from app.worker.llm.exceptions import (
    AllProvidersFailedError,
    InvalidResponseError,
)
from app.worker.llm.key_rotator import get_key_rotator

logger = logging.getLogger(__name__)


class ExternalLLMService:
    """
    External LLM Service - 공개 데이터 전용

    역할:
    - 뉴스/공시/정책 분석 및 요약
    - 업종별 인텔리전스 집계
    - 시그널 후보 식별

    🔓 공개 데이터만 처리:
    - 뉴스, DART 공시, 정책/규제, 산업 리포트
    """

    # External LLM 모델 설정
    ANALYSIS_MODELS = [
        {"model": "claude-3-5-sonnet-20240620", "provider": "anthropic"},
        {"model": "gpt-4o", "provider": "openai"},
    ]

    PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
    PERPLEXITY_MODEL = "sonar-pro"

    MAX_RETRIES = 3
    INITIAL_DELAY = 1.0
    TIMEOUT = 30.0

    def __init__(self):
        self._configure_api_keys()
        # Use Key Rotator for Perplexity API key (supports _1, _2, _3 rotation)
        self.key_rotator = get_key_rotator()
        self.perplexity_api_key = self.key_rotator.get_key("perplexity")
        self.perplexity_enabled = bool(self.perplexity_api_key)

    def _configure_api_keys(self):
        """API 키 설정"""
        # External LLM용 별도 키 우선 사용
        import os
        external_anthropic = os.getenv("EXTERNAL_LLM_ANTHROPIC_KEY", settings.ANTHROPIC_API_KEY)
        external_openai = os.getenv("EXTERNAL_LLM_OPENAI_KEY", settings.OPENAI_API_KEY)

        if external_anthropic:
            litellm.anthropic_key = external_anthropic
        if external_openai:
            litellm.openai_key = external_openai

    # =========================================
    # 뉴스/이벤트 수집 및 분석
    # =========================================

    def search_external_news(
        self,
        query: str,
        industry_name: str = "",
        days: int = 30,
    ) -> list[dict]:
        """
        Perplexity API로 외부 뉴스 검색

        Args:
            query: 검색 쿼리 (기업명, 키워드 등)
            industry_name: 업종명 (컨텍스트용)
            days: 검색 기간 (일)

        Returns:
            list[dict]: 검색된 뉴스/이벤트 목록
        """
        if not self.perplexity_enabled:
            logger.warning("Perplexity API not configured - search disabled")
            return []

        try:
            prompt = self._build_search_prompt(query, industry_name, days)

            headers = {
                "Authorization": f"Bearer {self.perplexity_api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": self.PERPLEXITY_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a financial analyst searching for external news "
                            "and events. Focus on publicly available information only. "
                            "Return results in JSON format."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.1,
                "max_tokens": 2000,
            }

            with httpx.Client(timeout=self.TIMEOUT) as client:
                response = client.post(
                    self.PERPLEXITY_API_URL,
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()

            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")

            events = self._parse_news_events(content)
            logger.info(f"[External LLM] Found {len(events)} news events for query: {query}")

            return events

        except Exception as e:
            logger.error(f"[External LLM] News search failed: {e}")
            return []

    def analyze_news_article(
        self,
        title: str,
        content: str,
        source_url: str,
    ) -> dict:
        """
        개별 뉴스 기사 분석

        Args:
            title: 기사 제목
            content: 기사 본문
            source_url: 출처 URL

        Returns:
            dict: 분석 결과 (요약, 업종코드, 키워드, 센티먼트 등)
        """
        system_prompt = """You are a financial news analyst. Analyze the given news article and extract:
1. Brief summary in Korean (200 chars max)
2. Related industry codes (Korean standard industry classification)
3. Key entities (company names, people)
4. Keywords
5. Event category (INDUSTRY_SHOCK, POLICY_CHANGE, MARKET_TREND, COMPANY_NEWS, etc.)
6. Sentiment (POSITIVE, NEGATIVE, NEUTRAL)
7. Impact level (HIGH, MED, LOW)
8. Whether this could generate a risk signal (is_signal_candidate)

Return JSON:
{
    "summary_ko": "...",
    "industry_codes": ["C26", "C29"],
    "entities": {"companies": [], "people": []},
    "keywords": [],
    "event_category": "...",
    "sentiment": "...",
    "impact_level": "...",
    "is_signal_candidate": true/false,
    "signal_type_hint": "INDUSTRY" or "ENVIRONMENT" (if is_signal_candidate)
}"""

        user_prompt = f"""Analyze this news article:

Title: {title}
Source: {source_url}

Content:
{content[:3000]}

Extract the required information."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            result = self._call_with_fallback(
                messages=messages,
                response_format={"type": "json_object"},
            )
            return json.loads(result)
        except (json.JSONDecodeError, AllProvidersFailedError) as e:
            logger.error(f"[External LLM] News analysis failed: {e}")
            return {
                "summary_ko": title[:200],
                "industry_codes": [],
                "entities": {},
                "keywords": [],
                "event_category": "UNKNOWN",
                "sentiment": "NEUTRAL",
                "impact_level": "LOW",
                "is_signal_candidate": False,
            }

    # =========================================
    # 업종별 인텔리전스 집계
    # =========================================

    def aggregate_industry_intel(
        self,
        industry_code: str,
        news_summaries: list[dict],
        period_start: str,
        period_end: str,
    ) -> dict:
        """
        업종별 인텔리전스 집계 및 요약

        Args:
            industry_code: 업종 코드 (예: C26)
            news_summaries: 해당 기간 뉴스 요약 목록
            period_start: 집계 시작일 (YYYY-MM-DD)
            period_end: 집계 종료일 (YYYY-MM-DD)

        Returns:
            dict: 집계된 인텔리전스
        """
        if not news_summaries:
            return {
                "period_summary": f"{industry_code} 업종에 대한 주요 뉴스가 없습니다.",
                "key_events": [],
                "risk_factors": [],
                "opportunity_factors": [],
            }

        # 뉴스 요약 텍스트 구성
        news_text = "\n".join([
            f"- [{n.get('sentiment', 'N/A')}] {n.get('summary_ko', '')}"
            for n in news_summaries[:20]  # 최대 20개
        ])

        system_prompt = """You are an industry analyst. Aggregate news summaries and generate:
1. Period summary (Korean, 2-3 sentences)
2. Key events list
3. Identified risk factors
4. Identified opportunity factors

Return JSON:
{
    "period_summary": "이번 주 해당 업종은...",
    "key_events": [{"event": "...", "impact": "HIGH/MED/LOW"}],
    "risk_factors": [{"factor": "...", "severity": "HIGH/MED/LOW"}],
    "opportunity_factors": [{"factor": "...", "potential": "HIGH/MED/LOW"}]
}"""

        user_prompt = f"""Aggregate news for industry {industry_code}
Period: {period_start} ~ {period_end}

News summaries:
{news_text}

Generate an intelligence summary."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            result = self._call_with_fallback(
                messages=messages,
                response_format={"type": "json_object"},
            )
            return json.loads(result)
        except Exception as e:
            logger.error(f"[External LLM] Industry intel aggregation failed: {e}")
            return {
                "period_summary": f"{industry_code} 업종 분석 실패",
                "key_events": [],
                "risk_factors": [],
                "opportunity_factors": [],
            }

    # =========================================
    # 정책/규제 분석
    # =========================================

    def analyze_policy(
        self,
        policy_title: str,
        policy_content: str,
        issuing_body: str,
    ) -> dict:
        """
        정책/규제 문서 분석

        Args:
            policy_title: 정책명
            policy_content: 정책 내용
            issuing_body: 발행 기관 (금융위, 금감원 등)

        Returns:
            dict: 분석 결과 (요약, 영향 업종, 필요 조치 등)
        """
        system_prompt = """You are a regulatory analyst. Analyze the policy/regulation and extract:
1. Summary in Korean
2. Affected industries (codes)
3. Impact analysis
4. Required actions

Return JSON:
{
    "summary": "...",
    "affected_industries": ["C26", "K64"],
    "impact_analysis": "...",
    "action_required": "...",
    "effective_date": "YYYY-MM-DD or null"
}"""

        user_prompt = f"""Analyze this policy/regulation:

Title: {policy_title}
Issuing Body: {issuing_body}

Content:
{policy_content[:4000]}

Identify affected industries and required actions."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            result = self._call_with_fallback(
                messages=messages,
                response_format={"type": "json_object"},
            )
            return json.loads(result)
        except Exception as e:
            logger.error(f"[External LLM] Policy analysis failed: {e}")
            return {
                "summary": policy_title,
                "affected_industries": [],
                "impact_analysis": "",
                "action_required": "",
                "effective_date": None,
            }

    # =========================================
    # 헬퍼 메서드
    # =========================================

    def _call_with_fallback(
        self,
        messages: list[dict],
        response_format: Optional[dict] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> str:
        """Fallback 체인을 사용한 LLM 호출"""
        errors = []

        for model_config in self.ANALYSIS_MODELS:
            model = model_config["model"]

            try:
                logger.info(f"[External LLM] Calling {model}")

                kwargs = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }

                if response_format:
                    kwargs["response_format"] = response_format

                response = completion(**kwargs)
                content = response.choices[0].message.content

                logger.info(f"[External LLM] Success from {model}")
                return content

            except Exception as e:
                errors.append({"model": model, "error": str(e)})
                logger.warning(f"[External LLM] {model} failed: {e}")

        raise AllProvidersFailedError(
            message="[External LLM] All providers failed",
            errors=errors,
        )

    def _build_search_prompt(self, query: str, industry_name: str, days: int) -> str:
        """검색 프롬프트 생성"""
        today = datetime.now().strftime("%Y-%m-%d")

        return f"""Search for recent news and events (last {days} days) related to:

Query: {query}
Industry: {industry_name}

Find information about:
1. Regulatory or legal issues
2. Industry-wide events or shocks
3. Financial news (earnings, debt)
4. Leadership or ownership changes
5. Policy or regulation changes

Today's date: {today}

Return JSON array:
[
  {{
    "title": "...",
    "summary": "Brief summary",
    "source_url": "URL",
    "published_at": "YYYY-MM-DD",
    "relevance": "HIGH/MED/LOW"
  }}
]

If no relevant events, return: []"""

    def _parse_news_events(self, content: str) -> list[dict]:
        """Perplexity 응답에서 뉴스 이벤트 파싱"""
        try:
            start_idx = content.find("[")
            end_idx = content.rfind("]") + 1

            if start_idx == -1 or end_idx == 0:
                return []

            json_str = content[start_idx:end_idx]
            events = json.loads(json_str)

            # 필수 필드 검증
            valid_events = []
            for event in events:
                if event.get("title") and event.get("summary"):
                    # URL 해시 생성
                    url = event.get("source_url", "")
                    if url:
                        event["url_hash"] = hashlib.sha256(url.encode()).hexdigest()
                    valid_events.append(event)

            return valid_events

        except json.JSONDecodeError:
            return []

    @staticmethod
    def generate_url_hash(url: str) -> str:
        """URL의 SHA256 해시 생성"""
        return hashlib.sha256(url.encode()).hexdigest()


def get_external_llm() -> ExternalLLMService:
    """External LLM 서비스 인스턴스 반환"""
    return ExternalLLMService()
