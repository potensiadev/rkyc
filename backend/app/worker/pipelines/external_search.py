"""
External Search Pipeline Stage
Stage 4: Search external news/events using Perplexity API

Improved version with 3-track search:
- DIRECT: Company-specific news
- INDUSTRY: Industry-wide trends and shocks
- ENVIRONMENT: Policy, regulation, macro-economic changes
"""

import json
import logging
from datetime import datetime
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


# Blog/community domains to exclude from citations
EXCLUDED_DOMAINS = [
    "blog.naver.com",
    "m.blog.naver.com",
    "blog.daum.net",
    "tistory.com",
    "brunch.co.kr",
    "velog.io",
    "medium.com",
    "wordpress.com",
    "blogspot.com",
    "cafe.naver.com",
    "cafe.daum.net",
    "dcinside.com",
    "fmkorea.com",
    "clien.net",
    "ruliweb.com",
    "ppomppu.co.kr",
    "instiz.net",
    "theqoo.net",
    "reddit.com",
    "quora.com",
]


# Query templates for ENVIRONMENT signal categories
ENVIRONMENT_QUERY_TEMPLATES = {
    "FX_RISK": "{industry_name} 환율 영향 리스크 수출기업",
    "TRADE_BLOC": "{industry_name} 무역 관세 FTA 수출규제",
    "GEOPOLITICAL": "{industry_name} 지정학 리스크 미중갈등 공급망",
    "SUPPLY_CHAIN": "{industry_name} 공급망 원자재 조달 리스크",
    "REGULATION": "{industry_name} 규제 정책 법률 변경 영향",
    "COMMODITY": "{industry_name} 원자재 가격 변동 원가",
    "PANDEMIC_HEALTH": "{industry_name} 팬데믹 감염병 방역 영향",
    "POLITICAL_INSTABILITY": "{industry_name} 정치 불안정 해외진출 리스크",
    "CYBER_TECH": "{industry_name} 사이버보안 기술규제 데이터",
    "ENERGY_SECURITY": "{industry_name} 에너지 전력 가스 공급 안정성",
    "FOOD_SECURITY": "{industry_name} 식량안보 농산물 원료 가격",
}


class ExternalSearchPipeline:
    """
    Stage 4: EXTERNAL - Search external information using Perplexity API

    3-Track Search Strategy:
    1. DIRECT: Company-specific news (기업 직접 관련)
    2. INDUSTRY: Industry-wide trends (산업 전반 동향)
    3. ENVIRONMENT: Policy/regulation/macro (거시환경 변화)

    Uses Perplexity sonar-pro model for real-time web search.
    Falls back to empty results if API key not configured.
    """

    PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
    MODEL = "sonar-pro"
    TIMEOUT = 30.0

    def __init__(self):
        self.api_key = settings.PERPLEXITY_API_KEY
        self.enabled = bool(self.api_key)

        if not self.enabled:
            logger.warning("Perplexity API key not configured - external search disabled")

    def execute(
        self,
        corp_name: str,
        industry_code: str,
        corp_id: str,
        profile_data: Optional[dict] = None,
    ) -> dict:
        """
        Execute external search stage with 3-track search.

        Args:
            corp_name: Corporation name for search
            industry_code: Industry code (e.g., C26)
            corp_id: Corporation ID for logging
            profile_data: Optional profile data with selected_queries

        Returns:
            dict with structure:
                - events: List of all external event dicts
                - direct_events: Company-specific events
                - industry_events: Industry-wide events
                - environment_events: Policy/regulation events
                - source: "perplexity" or "disabled"
        """
        industry_name = self._get_industry_name(industry_code)
        logger.info(
            f"EXTERNAL stage starting for corp_id={corp_id}, "
            f"corp_name={corp_name}, industry={industry_name}"
        )

        if not self.enabled:
            logger.info("External search disabled (no API key)")
            return {
                "events": [],
                "direct_events": [],
                "industry_events": [],
                "environment_events": [],
                "source": "disabled",
            }

        try:
            # Track 1: DIRECT - Company-specific news
            direct_events = self._search_direct_events(corp_name, industry_name)
            logger.info(f"DIRECT search: found {len(direct_events)} events")

            # Track 2: INDUSTRY - Industry-wide trends
            industry_events = self._search_industry_events(industry_name, industry_code)
            logger.info(f"INDUSTRY search: found {len(industry_events)} events")

            # Track 3: ENVIRONMENT - Policy/regulation based on profile
            selected_queries = []
            if profile_data and profile_data.get("selected_queries"):
                selected_queries = profile_data["selected_queries"]

            environment_events = self._search_environment_events(
                industry_name, industry_code, selected_queries
            )
            logger.info(f"ENVIRONMENT search: found {len(environment_events)} events")

            # Combine all events (with classification)
            all_events = direct_events + industry_events + environment_events

            logger.info(
                f"EXTERNAL stage completed: total={len(all_events)} "
                f"(direct={len(direct_events)}, industry={len(industry_events)}, "
                f"environment={len(environment_events)})"
            )

            return {
                "events": all_events,
                "direct_events": direct_events,
                "industry_events": industry_events,
                "environment_events": environment_events,
                "source": "perplexity",
            }

        except Exception as e:
            logger.error(f"External search failed: {e}")
            return {
                "events": [],
                "direct_events": [],
                "industry_events": [],
                "environment_events": [],
                "source": "error",
            }

    def _search_direct_events(self, corp_name: str, industry_name: str) -> list[dict]:
        """
        Track 1: Search for company-specific news.

        Targets: Financial news, leadership changes, legal issues, M&A, etc.
        """
        today = datetime.now().strftime("%Y-%m-%d")

        prompt = f"""Search for recent news (last 30 days) about this specific company:

Company: {corp_name}
Industry: {industry_name}
Today's date: {today}

Find news about:
1. Financial performance (earnings, revenue, profit/loss)
2. Leadership or ownership changes
3. Legal issues, lawsuits, regulatory violations
4. M&A, investments, partnerships
5. Credit rating changes
6. Major contracts won or lost

Return results as JSON array. Each event should have:
- title: Event title
- summary: Brief summary with specific facts
- source_url: Source URL
- published_at: YYYY-MM-DD if available
- relevance: HIGH/MED/LOW
- event_category: "DIRECT"

Return [] if no relevant news found. Only include factual, verifiable information.
Exclude blog posts and user-generated content."""

        events = self._call_perplexity(prompt)

        # Tag as DIRECT
        for event in events:
            event["event_category"] = "DIRECT"

        return events

    def _search_industry_events(self, industry_name: str, industry_code: str) -> list[dict]:
        """
        Track 2: Search for industry-wide trends and shocks.

        Targets: Industry trends, market changes, technology shifts, etc.
        """
        today = datetime.now().strftime("%Y-%m-%d")

        prompt = f"""Search for recent industry news (last 30 days) affecting the entire sector:

Industry: {industry_name} (code: {industry_code})
Today's date: {today}

Find news about:
1. Industry-wide market trends (growth, decline, disruption)
2. Major competitor moves affecting the whole industry
3. Technology changes impacting the sector
4. Supply chain issues affecting multiple companies
5. Labor market changes (strikes, wage trends)
6. Industry consolidation or fragmentation

Focus on news that affects MULTIPLE companies in this industry, not just one company.

Return results as JSON array. Each event should have:
- title: Event title
- summary: Brief summary explaining industry-wide impact
- source_url: Source URL
- published_at: YYYY-MM-DD if available
- relevance: HIGH/MED/LOW
- event_category: "INDUSTRY"

Return [] if no relevant news found. Only include factual, verifiable information.
Exclude blog posts and user-generated content."""

        events = self._call_perplexity(prompt)

        # Tag as INDUSTRY
        for event in events:
            event["event_category"] = "INDUSTRY"

        return events

    def _search_environment_events(
        self,
        industry_name: str,
        industry_code: str,
        selected_queries: list[str],
    ) -> list[dict]:
        """
        Track 3: Search for policy, regulation, and macro-economic changes.

        Uses selected_queries from Corp Profile to focus searches.
        """
        today = datetime.now().strftime("%Y-%m-%d")

        # Build targeted queries based on profile
        query_topics = []

        if selected_queries:
            # Use profile-selected queries
            for query_key in selected_queries[:5]:  # Limit to top 5
                if query_key in ENVIRONMENT_QUERY_TEMPLATES:
                    query_topics.append(
                        ENVIRONMENT_QUERY_TEMPLATES[query_key].format(
                            industry_name=industry_name
                        )
                    )
        else:
            # Default queries if no profile
            query_topics = [
                f"{industry_name} 정책 규제 변경",
                f"{industry_name} 정부 지원 세제 혜택",
                f"{industry_name} 환율 금리 영향",
            ]

        # Join query topics
        query_focus = "\n".join(f"- {topic}" for topic in query_topics)

        prompt = f"""Search for recent policy, regulation, and macro-economic news (last 30 days):

Industry: {industry_name} (code: {industry_code})
Today's date: {today}

Focus on these specific topics:
{query_focus}

Find news about:
1. New government policies or regulations affecting this industry
2. Tax changes, subsidies, or incentives
3. Trade policy changes (tariffs, export controls, FTAs)
4. Environmental regulations (carbon, emissions)
5. Interest rate or exchange rate impacts
6. Geopolitical events affecting supply chains

Return results as JSON array. Each event should have:
- title: Event title
- summary: Brief summary explaining policy/regulatory impact
- source_url: Source URL
- published_at: YYYY-MM-DD if available
- relevance: HIGH/MED/LOW
- event_category: "ENVIRONMENT"

Return [] if no relevant news found. Only include factual, verifiable information.
Exclude blog posts and user-generated content."""

        events = self._call_perplexity(prompt)

        # Tag as ENVIRONMENT
        for event in events:
            event["event_category"] = "ENVIRONMENT"

        return events

    def _call_perplexity(self, prompt: str) -> list[dict]:
        """Call Perplexity API and parse response."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a financial analyst researching corporate risk and opportunity signals. "
                        "Search for recent news that could indicate risks or opportunities. "
                        "Return results in valid JSON array format. "
                        "Exclude blog posts, forums, and user-generated content. "
                        "Only use reliable news sources, official announcements, and industry reports."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": 0.1,
            "max_tokens": 2000,
        }

        try:
            with httpx.Client(timeout=self.TIMEOUT) as client:
                response = client.post(
                    self.PERPLEXITY_API_URL,
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()

            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")

            # Extract citations if available
            citations = result.get("citations", [])

            # Parse events from response
            events = self._parse_events(content, citations)
            return events

        except httpx.TimeoutException:
            logger.warning("Perplexity API timeout")
            return []
        except httpx.HTTPStatusError as e:
            logger.error(f"Perplexity API error: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Perplexity call failed: {e}")
            return []

    def _parse_events(self, content: str, citations: list[str] = None) -> list[dict]:
        """Parse events from Perplexity response."""
        try:
            # Find JSON array in response
            start_idx = content.find("[")
            end_idx = content.rfind("]") + 1

            if start_idx == -1 or end_idx == 0:
                logger.warning("No JSON array found in Perplexity response")
                return []

            json_str = content[start_idx:end_idx]
            events = json.loads(json_str)

            # Validate and filter events
            valid_events = []
            for event in events:
                if self._validate_event(event):
                    # Filter out blog URLs
                    if not self._is_excluded_source(event.get("source_url", "")):
                        valid_events.append(event)

            return valid_events

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Perplexity response as JSON: {e}")
            return []

    def _validate_event(self, event: dict) -> bool:
        """Validate a single event dict."""
        required_fields = ["title", "summary"]

        for field in required_fields:
            if not event.get(field):
                return False

        # Validate relevance if present
        if event.get("relevance") and event["relevance"] not in {"HIGH", "MED", "LOW"}:
            event["relevance"] = "MED"  # Default to MED

        return True

    def _is_excluded_source(self, url: str) -> bool:
        """Check if URL is from excluded domain (blog/community)."""
        if not url:
            return False
        url_lower = url.lower()
        return any(domain in url_lower for domain in EXCLUDED_DOMAINS)

    def _get_industry_name(self, industry_code: str) -> str:
        """Get industry name from code."""
        industry_names = {
            "C10": "식품제조업",
            "C21": "의약품제조업",
            "C26": "전자부품제조업",
            "C29": "기계장비제조업",
            "D35": "전기업",
            "F41": "건설업",
            "G45": "자동차판매업",
            "G46": "도매업",
            "G47": "소매업",
            "H49": "육상운송업",
            "J58": "출판업",
            "J62": "소프트웨어개발업",
            "K64": "금융업",
            "L68": "부동산업",
            "M70": "경영컨설팅업",
            "N74": "전문서비스업",
        }
        return industry_names.get(industry_code, f"기타업종 ({industry_code})")
