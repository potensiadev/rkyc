"""
External Search Pipeline Stage
Stage 4: Search external news/events using Perplexity API

Production-grade 3-track search with:
- DIRECT: Company-specific credit risk signals
- INDUSTRY: Sector-wide trends and shocks
- ENVIRONMENT: Policy, regulation, macro-economic changes

Optimized for Korean financial institution use cases.

Sprint 1 Enhancement (ADR-009):
- 3-Track 병렬 실행으로 40% 속도 향상 (20초 → 12초)
- asyncio + httpx.AsyncClient 사용
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Optional

import httpx

from app.core.config import settings
from app.worker.llm.key_rotator import get_key_rotator

logger = logging.getLogger(__name__)


# =============================================================================
# Source Quality Configuration
# =============================================================================

# Domains to exclude from citations (blogs, user-generated content)
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

# Priority sources for Korean corporate news
PRIORITY_SOURCES = {
    "tier1": ["dart.fss.or.kr", "kind.krx.co.kr", ".go.kr"],  # 공시, 정부
    "tier2": ["hankyung.com", "mk.co.kr", "sedaily.com", "edaily.co.kr"],  # 주요 경제지
    "tier3": ["yna.co.kr", "newsis.com", "news1.kr"],  # 통신사
}


# =============================================================================
# Industry-Specific Keywords
# =============================================================================

INDUSTRY_KEYWORDS = {
    "C10": {  # 식품제조업
        "supply_chain": ["농산물", "원료", "식자재", "수입", "가격"],
        "regulation": ["식약처", "HACCP", "위생", "표시제", "영양성분"],
        "market": ["소비자", "유통", "마트", "편의점", "프랜차이즈"],
    },
    "C21": {  # 의약품제조업
        "supply_chain": ["원료의약품", "API", "바이오", "CMO", "CDMO"],
        "regulation": ["식약처", "FDA", "EMA", "임상시험", "허가", "약가"],
        "market": ["신약", "제네릭", "바이오시밀러", "건강보험", "급여"],
    },
    "C26": {  # 전자부품제조업
        "supply_chain": ["반도체", "디스플레이", "배터리", "소재", "장비"],
        "regulation": ["수출규제", "기술이전", "IRA", "CHIPS법", "탄소중립"],
        "market": ["AI", "HBM", "전기차", "스마트폰", "데이터센터"],
    },
    "C29": {  # 기계장비제조업
        "supply_chain": ["철강", "알루미늄", "유압", "베어링", "모터"],
        "regulation": ["안전인증", "환경규제", "탄소세", "에너지효율"],
        "market": ["자동화", "로봇", "스마트공장", "수주", "플랜트"],
    },
    "D35": {  # 전기업
        "supply_chain": ["연료", "LNG", "석탄", "재생에너지", "ESS"],
        "regulation": ["전기요금", "RPS", "RE100", "탄소배출권", "원전"],
        "market": ["전력수요", "피크", "계통", "송전", "배전"],
    },
    "F41": {  # 건설업
        "supply_chain": ["시멘트", "레미콘", "철근", "인건비", "자재"],
        "regulation": ["분양가상한제", "재건축", "인허가", "안전점검"],
        "market": ["분양", "미분양", "PF", "부동산", "금리"],
    },
}

# Default keywords for industries not in the map
DEFAULT_INDUSTRY_KEYWORDS = {
    "supply_chain": ["원자재", "부품", "조달", "물류", "재고"],
    "regulation": ["규제", "인허가", "정책", "법률", "감독"],
    "market": ["수요", "경쟁", "시장점유율", "가격", "고객"],
}


# =============================================================================
# Query templates for ENVIRONMENT signal categories
# =============================================================================

ENVIRONMENT_QUERY_TEMPLATES = {
    "FX_RISK": "{industry_name} 환율 영향 리스크 수출기업 원/달러",
    "TRADE_BLOC": "{industry_name} 무역 관세 FTA 수출규제 통상",
    "GEOPOLITICAL": "{industry_name} 지정학 리스크 미중갈등 공급망 탈중국",
    "SUPPLY_CHAIN": "{industry_name} 공급망 원자재 조달 리스크 재고",
    "REGULATION": "{industry_name} 규제 정책 법률 변경 영향 정부",
    "COMMODITY": "{industry_name} 원자재 가격 변동 원가 상승 하락",
    "PANDEMIC_HEALTH": "{industry_name} 팬데믹 감염병 방역 영향 공장",
    "POLITICAL_INSTABILITY": "{industry_name} 정치 불안정 해외진출 리스크 국가",
    "CYBER_TECH": "{industry_name} 사이버보안 기술규제 데이터 개인정보",
    "ENERGY_SECURITY": "{industry_name} 에너지 전력 가스 공급 안정성 요금",
    "FOOD_SECURITY": "{industry_name} 식량안보 농산물 원료 가격 수입",
}


class ExternalSearchPipeline:
    """
    Stage 4: EXTERNAL - Search external information using Perplexity API

    Production-grade 3-Track Search Strategy:
    1. DIRECT: Company-specific credit risk signals (우선순위별)
    2. INDUSTRY: Sector-wide trends with industry-specific keywords
    3. ENVIRONMENT: Policy/regulation/macro based on corp profile

    Uses Perplexity sonar-pro model for real-time web search.

    Sprint 1 Enhancement (ADR-009):
    - parallel_mode=True: 3-Track 동시 실행 (40% speedup)
    - asyncio + httpx.AsyncClient 사용
    """

    PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
    MODEL = "sonar-pro"
    TIMEOUT = 45.0  # Increased for comprehensive search

    def __init__(self, parallel_mode: bool = True):
        # Use Key Rotator to get Perplexity API key (supports _1, _2, _3 rotation)
        self.key_rotator = get_key_rotator()
        self.api_key = self.key_rotator.get_key("perplexity")
        self.enabled = bool(self.api_key)
        self.parallel_mode = parallel_mode

        if not self.enabled:
            logger.warning("Perplexity API key not configured - external search disabled")
        else:
            logger.info("Perplexity API key loaded via Key Rotator")

    def execute(
        self,
        corp_name: str,
        industry_code: str,
        corp_id: str,
        profile_data: Optional[dict] = None,
        corp_reg_no: Optional[str] = None,
    ) -> dict:
        """
        Execute external search stage with 3-track search.

        ADR-009 Enhancement:
        - parallel_mode=True: 3-Track 동시 실행 (40% speedup)
        - parallel_mode=False: 기존 순차 실행

        Args:
            corp_name: Corporation name for search
            industry_code: Industry code (e.g., C26)
            corp_id: Corporation ID for logging
            profile_data: Optional profile data with selected_queries
            corp_reg_no: Optional corporate registration number

        Returns:
            dict with categorized events and metadata
        """
        industry_name = self._get_industry_name(industry_code)
        logger.info(
            f"EXTERNAL stage starting for corp_id={corp_id}, "
            f"corp_name={corp_name}, industry={industry_name}, "
            f"parallel_mode={self.parallel_mode}"
        )

        if not self.enabled:
            logger.info("External search disabled (no API key)")
            return self._empty_result("disabled")

        try:
            selected_queries = []
            if profile_data and profile_data.get("selected_queries"):
                selected_queries = profile_data["selected_queries"]

            if self.parallel_mode:
                return self._execute_parallel(
                    corp_name, industry_name, industry_code,
                    corp_reg_no, selected_queries
                )
            else:
                return self._execute_sequential(
                    corp_name, industry_name, industry_code,
                    corp_reg_no, selected_queries
                )

        except Exception as e:
            logger.error(f"External search failed: {e}")
            return self._empty_result("error")

    def _execute_parallel(
        self,
        corp_name: str,
        industry_name: str,
        industry_code: str,
        corp_reg_no: Optional[str],
        selected_queries: list[str],
    ) -> dict:
        """
        병렬 모드: 3-Track 동시 실행

        ADR-009 Sprint 1 구현:
        - asyncio.gather()로 3개 API 동시 호출
        - 개별 실패는 빈 리스트로 처리 (Graceful Degradation)
        """
        import time
        start_time = time.time()

        async def run_parallel():
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                tasks = [
                    self._search_direct_events_async(
                        client, corp_name, industry_name, corp_reg_no
                    ),
                    self._search_industry_events_async(
                        client, corp_name, industry_name, industry_code
                    ),
                    self._search_environment_events_async(
                        client, industry_name, industry_code, selected_queries
                    ),
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                return results

        # P0-3 Fix: 안전한 asyncio 이벤트 루프 실행
        # Celery Worker 환경에서도 안전하게 동작하도록 개선
        import concurrent.futures

        def run_in_new_loop():
            """새 이벤트 루프에서 async 함수 실행 (Celery 호환)"""
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                return new_loop.run_until_complete(run_parallel())
            finally:
                new_loop.close()

        try:
            # 먼저 현재 이벤트 루프 확인 (Python 3.10+ 호환)
            try:
                loop = asyncio.get_running_loop()
                # 이미 실행 중인 루프가 있는 경우 (Celery/FastAPI 등)
                # 별도 스레드에서 새 이벤트 루프 사용
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(run_in_new_loop)
                    results = future.result(timeout=60.0)
            except RuntimeError:
                # 실행 중인 루프가 없는 경우 → 직접 asyncio.run 사용
                results = asyncio.run(run_parallel())

        except concurrent.futures.TimeoutError:
            logger.error("Parallel external search timed out after 60s")
            results = [[], [], []]
        except Exception as e:
            logger.error(f"Parallel external search failed: {e}")
            results = [[], [], []]

        # 결과 처리
        direct_events = results[0] if not isinstance(results[0], Exception) else []
        industry_events = results[1] if not isinstance(results[1], Exception) else []
        environment_events = results[2] if not isinstance(results[2], Exception) else []

        # 예외 로깅
        for i, (name, result) in enumerate([
            ("DIRECT", results[0]),
            ("INDUSTRY", results[1]),
            ("ENVIRONMENT", results[2])
        ]):
            if isinstance(result, Exception):
                logger.warning(f"{name} search failed in parallel mode: {result}")

        elapsed_ms = int((time.time() - start_time) * 1000)
        all_events = direct_events + industry_events + environment_events

        logger.info(
            f"EXTERNAL parallel completed in {elapsed_ms}ms: total={len(all_events)} "
            f"(direct={len(direct_events)}, industry={len(industry_events)}, "
            f"environment={len(environment_events)})"
        )

        return {
            "events": all_events,
            "direct_events": direct_events,
            "industry_events": industry_events,
            "environment_events": environment_events,
            "source": "perplexity",
            "metadata": {
                "search_timestamp": datetime.now().isoformat(),
                "parallel_mode": True,
                "execution_time_ms": elapsed_ms,
                "events_count": {
                    "direct": len(direct_events),
                    "industry": len(industry_events),
                    "environment": len(environment_events),
                    "total": len(all_events),
                },
            },
        }

    def _execute_sequential(
        self,
        corp_name: str,
        industry_name: str,
        industry_code: str,
        corp_reg_no: Optional[str],
        selected_queries: list[str],
    ) -> dict:
        """순차 모드: 기존 방식"""
        import time
        start_time = time.time()

        # Track 1: DIRECT - Company-specific credit risk signals
        direct_events = self._search_direct_events(
            corp_name, industry_name, corp_reg_no
        )
        logger.info(f"DIRECT search: found {len(direct_events)} events")

        # Track 2: INDUSTRY - Sector-wide trends with keywords
        industry_events = self._search_industry_events(
            corp_name, industry_name, industry_code
        )
        logger.info(f"INDUSTRY search: found {len(industry_events)} events")

        # Track 3: ENVIRONMENT - Policy/regulation based on profile
        environment_events = self._search_environment_events(
            industry_name, industry_code, selected_queries
        )
        logger.info(f"ENVIRONMENT search: found {len(environment_events)} events")

        # Combine all events
        all_events = direct_events + industry_events + environment_events
        elapsed_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"EXTERNAL sequential completed in {elapsed_ms}ms: total={len(all_events)} "
            f"(direct={len(direct_events)}, industry={len(industry_events)}, "
            f"environment={len(environment_events)})"
        )

        return {
            "events": all_events,
            "direct_events": direct_events,
            "industry_events": industry_events,
            "environment_events": environment_events,
            "source": "perplexity",
            "metadata": {
                "search_timestamp": datetime.now().isoformat(),
                "parallel_mode": False,
                "execution_time_ms": elapsed_ms,
                "events_count": {
                    "direct": len(direct_events),
                    "industry": len(industry_events),
                    "environment": len(environment_events),
                    "total": len(all_events),
                },
            },
        }

    def _empty_result(self, source: str) -> dict:
        """Return empty result structure."""
        return {
            "events": [],
            "direct_events": [],
            "industry_events": [],
            "environment_events": [],
            "source": source,
            "metadata": {
                "search_timestamp": datetime.now().isoformat(),
                "events_count": {"direct": 0, "industry": 0, "environment": 0, "total": 0},
            },
        }

    def _search_direct_events(
        self,
        corp_name: str,
        industry_name: str,
        corp_reg_no: Optional[str] = None,
    ) -> list[dict]:
        """
        Track 1: Search for company-specific credit risk signals.

        Priority order:
        1. Credit Risk Indicators (RISK focus)
        2. Business Events (RISK/OPPORTUNITY)
        3. Financial Performance
        """
        today = datetime.now().strftime("%Y-%m-%d")

        prompt = f"""# Search Context
Target Company: {corp_name}
{f"Corporate Registration: {corp_reg_no}" if corp_reg_no else ""}
Industry: {industry_name}
Time Window: Last 30 days
Today's date: {today}

# Search Objectives
Find VERIFIED news about this SPECIFIC company:

## Priority 1: Credit Risk Indicators (RISK focus)
- Payment defaults, debt restructuring, credit rating downgrades
- Regulatory violations, lawsuits, fraud allegations
- Executive departures, governance issues
- Factory closures, layoffs, asset sales

## Priority 2: Business Events (RISK/OPPORTUNITY)
- M&A announcements (acquirer or target)
- Major contract wins or losses (>10% revenue impact)
- New market entry or exit
- Strategic partnerships or joint ventures

## Priority 3: Financial Performance
- Earnings surprises (beat/miss by >10%)
- Revenue trend changes
- Margin compression or expansion
- Cash flow concerns

# Output Requirements
Return results as JSON array with this structure:
[
  {{
    "title": "Event title (Korean)",
    "headline": "15자 이내 핵심 요약",
    "summary": "Brief summary with specific facts (100자 이내)",
    "source_url": "Source URL",
    "source_name": "Source name (e.g., 한국경제, DART)",
    "published_at": "YYYY-MM-DD if available",
    "relevance": "HIGH/MED/LOW",
    "risk_type": "credit_risk|business_event|financial_performance",
    "impact_direction": "RISK|OPPORTUNITY|NEUTRAL"
  }}
]

# Quality Filter
- Korean language sources preferred
- Prioritize: 공시(DART), 주요 경제지(한경/매경/서울경제), 통신사(연합뉴스)
- FACT-BASED news only (no speculation, no rumors)
- Exclude: 블로그, 커뮤니티, 광고성 기사

Return [] if no relevant news found."""

        events = self._call_perplexity(prompt, "direct")

        # Tag as DIRECT
        for event in events:
            event["event_category"] = "DIRECT"

        return events

    def _search_industry_events(
        self,
        corp_name: str,
        industry_name: str,
        industry_code: str,
    ) -> list[dict]:
        """
        Track 2: Search for industry-wide trends and shocks.

        5 key areas with industry-specific keywords.
        """
        today = datetime.now().strftime("%Y-%m-%d")

        # Get industry-specific keywords
        keywords = INDUSTRY_KEYWORDS.get(industry_code, DEFAULT_INDUSTRY_KEYWORDS)
        supply_keywords = ", ".join(keywords.get("supply_chain", []))
        regulation_keywords = ", ".join(keywords.get("regulation", []))
        market_keywords = ", ".join(keywords.get("market", []))

        prompt = f"""# Search Context
Target Industry: {industry_name} (code: {industry_code})
Related Company for Context: {corp_name}
Time Window: Last 30 days
Today's date: {today}

# Industry-Specific Keywords
- Supply Chain: {supply_keywords}
- Regulation: {regulation_keywords}
- Market: {market_keywords}

# Search Objectives
Find industry-wide events affecting MULTIPLE companies in this sector:

## 1. Market Structure Changes
- Major M&A reshaping competitive landscape
- New market entrants (especially foreign competitors)
- Industry consolidation or fragmentation
- Bankruptcy of significant players

## 2. Supply Chain Dynamics
- Raw material price volatility ({supply_keywords})
- Logistics disruptions affecting the sector
- Supplier/vendor ecosystem changes
- Inventory buildup or shortage signals

## 3. Demand Signals
- End-market demand shifts
- Customer industry health (B2B context)
- Seasonal pattern deviations
- New application/use case emergence

## 4. Technology & Innovation
- Disruptive technology threats
- Automation/digitalization pressures
- R&D breakthroughs in the sector
- Patent/IP developments

## 5. Labor Market
- Industry-wide hiring/layoff trends
- Wage pressure in key skill areas
- Union activities, strikes
- Talent migration patterns

# Output Requirements
Return results as JSON array:
[
  {{
    "title": "Event title (Korean)",
    "headline": "15자 이내 핵심 요약",
    "summary": "Brief summary explaining industry-wide impact (100자 이내)",
    "source_url": "Source URL",
    "source_name": "Source name",
    "published_at": "YYYY-MM-DD if available",
    "relevance": "HIGH/MED/LOW",
    "impact_area": "market_structure|supply_chain|demand|technology|labor",
    "impact_direction": "RISK|OPPORTUNITY|NEUTRAL",
    "affected_scope": "Description of which companies/segments affected"
  }}
]

# Quality Filter
- Focus on events impacting MULTIPLE companies, not single-company news
- Quantify market impact where possible (market size, growth rates)
- Korean sources: 산업통상자원부, 업종별 협회, 한국은행 산업동향
- Exclude: Single company earnings (unless industry bellwether), stock price movements without fundamental cause

Return [] if no relevant news found."""

        events = self._call_perplexity(prompt, "industry")

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
                f"{industry_name} 정책 규제 변경 정부 발표",
                f"{industry_name} 세제 혜택 보조금 지원",
                f"{industry_name} 환율 금리 영향 수출",
            ]

        query_focus = "\n".join(f"- {topic}" for topic in query_topics)

        prompt = f"""# Search Context
Target Industry: {industry_name} (code: {industry_code})
Time Window: Last 30 days
Today's date: {today}

# Focused Search Topics
{query_focus}

# Search Objectives
Find policy, regulation, and macro-economic news:

## 1. Government Policy
- New policies or regulations affecting this industry
- Implementation timeline and scope
- Enforcement actions or penalties

## 2. Fiscal & Tax
- Tax changes, subsidies, or incentives
- Budget allocations for industry support
- Tariff changes

## 3. Trade & Geopolitics
- Trade policy changes (FTA, export controls)
- Geopolitical tensions affecting supply chains
- Sanctions or trade restrictions

## 4. Environmental & ESG
- Carbon regulations, emission standards
- ESG disclosure requirements
- Green taxonomy impacts

## 5. Monetary & Financial
- Interest rate impacts on industry
- Exchange rate volatility effects
- Credit market conditions

# Output Requirements
Return results as JSON array:
[
  {{
    "title": "Event title (Korean)",
    "headline": "15자 이내 핵심 요약",
    "summary": "Brief summary explaining policy/regulatory impact (100자 이내)",
    "source_url": "Source URL",
    "source_name": "Source name",
    "published_at": "YYYY-MM-DD if available",
    "relevance": "HIGH/MED/LOW",
    "policy_area": "government|fiscal|trade|environmental|monetary",
    "impact_direction": "RISK|OPPORTUNITY|NEUTRAL",
    "effective_date": "If known, when policy takes effect"
  }}
]

# Quality Filter
- Prioritize: 정부 발표, 관보, 규제기관 공지
- Korean sources: 기획재정부, 산업부, 금융위, 한국은행
- FACT-BASED only (no speculation about future policy)

Return [] if no relevant news found."""

        events = self._call_perplexity(prompt, "environment")

        # Tag as ENVIRONMENT
        for event in events:
            event["event_category"] = "ENVIRONMENT"

        return events

    def _call_perplexity(self, prompt: str, search_type: str) -> list[dict]:
        """Call Perplexity API and parse response."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        system_content = """You are a senior financial analyst at a Korean bank researching corporate risk and opportunity signals.

Your role:
1. Find VERIFIED, FACT-BASED news only
2. Prioritize official sources (DART, government, major news outlets)
3. Return results in valid JSON array format
4. Use Korean language for titles and summaries
5. Be conservative - only include news with clear evidence

Quality standards:
- NO speculation or rumors
- NO blog posts or user-generated content
- NO promotional content
- Cross-reference controversial claims
- Include publication date when available"""

        payload = {
            "model": self.MODEL,
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 3000,
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
            citations = result.get("citations", [])

            events = self._parse_events(content, citations, search_type)
            return events

        except httpx.TimeoutException:
            logger.warning(f"Perplexity API timeout for {search_type} search")
            return []
        except httpx.HTTPStatusError as e:
            logger.error(f"Perplexity API error for {search_type}: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Perplexity call failed for {search_type}: {e}")
            return []

    def _parse_events(
        self,
        content: str,
        citations: list[str] = None,
        search_type: str = "unknown",
    ) -> list[dict]:
        """Parse events from Perplexity response."""
        try:
            # Find JSON array in response
            start_idx = content.find("[")
            end_idx = content.rfind("]") + 1

            if start_idx == -1 or end_idx == 0:
                logger.warning(f"No JSON array found in {search_type} response")
                return []

            json_str = content[start_idx:end_idx]
            events = json.loads(json_str)

            # Validate and filter events
            valid_events = []
            for event in events:
                if self._validate_event(event):
                    # Filter out excluded sources
                    if not self._is_excluded_source(event.get("source_url", "")):
                        # Add source quality tier
                        event["source_tier"] = self._get_source_tier(
                            event.get("source_url", "")
                        )
                        valid_events.append(event)

            logger.debug(f"Parsed {len(valid_events)} valid events from {search_type}")
            return valid_events

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse {search_type} response as JSON: {e}")
            return []

    def _validate_event(self, event: dict) -> bool:
        """Validate a single event dict."""
        required_fields = ["title", "summary"]

        for field in required_fields:
            if not event.get(field):
                return False

        # Validate relevance if present
        if event.get("relevance") and event["relevance"] not in {"HIGH", "MED", "LOW"}:
            event["relevance"] = "MED"

        # Validate impact_direction if present
        if event.get("impact_direction") and event["impact_direction"] not in {
            "RISK", "OPPORTUNITY", "NEUTRAL"
        }:
            event["impact_direction"] = "NEUTRAL"

        return True

    def _is_excluded_source(self, url: str) -> bool:
        """Check if URL is from excluded domain (blog/community)."""
        if not url:
            return False
        url_lower = url.lower()
        return any(domain in url_lower for domain in EXCLUDED_DOMAINS)

    def _get_source_tier(self, url: str) -> str:
        """Get source quality tier from URL."""
        if not url:
            return "tier4"
        url_lower = url.lower()

        for tier, domains in PRIORITY_SOURCES.items():
            if any(domain in url_lower for domain in domains):
                return tier

        return "tier4"  # Unknown/other sources

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

    # =========================================================================
    # Async Methods for Parallel Execution (ADR-009 Sprint 1)
    # =========================================================================

    async def _call_perplexity_async(
        self,
        client: httpx.AsyncClient,
        prompt: str,
        search_type: str,
    ) -> list[dict]:
        """Async version of Perplexity API call."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        system_content = """You are a senior financial analyst at a Korean bank researching corporate risk and opportunity signals.

Your role:
1. Find VERIFIED, FACT-BASED news only
2. Prioritize official sources (DART, government, major news outlets)
3. Return results in valid JSON array format
4. Use Korean language for titles and summaries
5. Be conservative - only include news with clear evidence

Quality standards:
- NO speculation or rumors
- NO blog posts or user-generated content
- NO promotional content
- Cross-reference controversial claims
- Include publication date when available"""

        payload = {
            "model": self.MODEL,
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 3000,
        }

        try:
            response = await client.post(
                self.PERPLEXITY_API_URL,
                headers=headers,
                json=payload,
            )
            response.raise_for_status()

            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            citations = result.get("citations", [])

            events = self._parse_events(content, citations, search_type)
            return events

        except httpx.TimeoutException:
            logger.warning(f"Perplexity API timeout for {search_type} search (async)")
            return []
        except httpx.HTTPStatusError as e:
            logger.error(f"Perplexity API error for {search_type}: {e.response.status_code} (async)")
            return []
        except Exception as e:
            logger.error(f"Perplexity call failed for {search_type}: {e} (async)")
            return []

    async def _search_direct_events_async(
        self,
        client: httpx.AsyncClient,
        corp_name: str,
        industry_name: str,
        corp_reg_no: Optional[str] = None,
    ) -> list[dict]:
        """Async version of DIRECT search."""
        today = datetime.now().strftime("%Y-%m-%d")

        prompt = f"""# Search Context
Target Company: {corp_name}
{f"Corporate Registration: {corp_reg_no}" if corp_reg_no else ""}
Industry: {industry_name}
Time Window: Last 30 days
Today's date: {today}

# Search Objectives
Find VERIFIED news about this SPECIFIC company:

## Priority 1: Credit Risk Indicators (RISK focus)
- Payment defaults, debt restructuring, credit rating downgrades
- Regulatory violations, lawsuits, fraud allegations
- Executive departures, governance issues
- Factory closures, layoffs, asset sales

## Priority 2: Business Events (RISK/OPPORTUNITY)
- M&A announcements (acquirer or target)
- Major contract wins or losses (>10% revenue impact)
- New market entry or exit
- Strategic partnerships or joint ventures

## Priority 3: Financial Performance
- Earnings surprises (beat/miss by >10%)
- Revenue trend changes
- Margin compression or expansion
- Cash flow concerns

# Output Requirements
Return results as JSON array with this structure:
[
  {{
    "title": "Event title (Korean)",
    "headline": "15자 이내 핵심 요약",
    "summary": "Brief summary with specific facts (100자 이내)",
    "source_url": "Source URL",
    "source_name": "Source name (e.g., 한국경제, DART)",
    "published_at": "YYYY-MM-DD if available",
    "relevance": "HIGH/MED/LOW",
    "risk_type": "credit_risk|business_event|financial_performance",
    "impact_direction": "RISK|OPPORTUNITY|NEUTRAL"
  }}
]

# Quality Filter
- Korean language sources preferred
- Prioritize: 공시(DART), 주요 경제지(한경/매경/서울경제), 통신사(연합뉴스)
- FACT-BASED news only (no speculation, no rumors)
- Exclude: 블로그, 커뮤니티, 광고성 기사

Return [] if no relevant news found."""

        events = await self._call_perplexity_async(client, prompt, "direct")

        # Tag as DIRECT
        for event in events:
            event["event_category"] = "DIRECT"

        return events

    async def _search_industry_events_async(
        self,
        client: httpx.AsyncClient,
        corp_name: str,
        industry_name: str,
        industry_code: str,
    ) -> list[dict]:
        """Async version of INDUSTRY search."""
        today = datetime.now().strftime("%Y-%m-%d")

        # Get industry-specific keywords
        keywords = INDUSTRY_KEYWORDS.get(industry_code, DEFAULT_INDUSTRY_KEYWORDS)
        supply_keywords = ", ".join(keywords.get("supply_chain", []))
        regulation_keywords = ", ".join(keywords.get("regulation", []))
        market_keywords = ", ".join(keywords.get("market", []))

        prompt = f"""# Search Context
Target Industry: {industry_name} (code: {industry_code})
Related Company for Context: {corp_name}
Time Window: Last 30 days
Today's date: {today}

# Industry-Specific Keywords
- Supply Chain: {supply_keywords}
- Regulation: {regulation_keywords}
- Market: {market_keywords}

# Search Objectives
Find industry-wide events affecting MULTIPLE companies in this sector:

## 1. Market Structure Changes
- Major M&A reshaping competitive landscape
- New market entrants (especially foreign competitors)
- Industry consolidation or fragmentation
- Bankruptcy of significant players

## 2. Supply Chain Dynamics
- Raw material price volatility ({supply_keywords})
- Logistics disruptions affecting the sector
- Supplier/vendor ecosystem changes
- Inventory buildup or shortage signals

## 3. Demand Signals
- End-market demand shifts
- Customer industry health (B2B context)
- Seasonal pattern deviations
- New application/use case emergence

## 4. Technology & Innovation
- Disruptive technology threats
- Automation/digitalization pressures
- R&D breakthroughs in the sector
- Patent/IP developments

## 5. Labor Market
- Industry-wide hiring/layoff trends
- Wage pressure in key skill areas
- Union activities, strikes
- Talent migration patterns

# Output Requirements
Return results as JSON array:
[
  {{
    "title": "Event title (Korean)",
    "headline": "15자 이내 핵심 요약",
    "summary": "Brief summary explaining industry-wide impact (100자 이내)",
    "source_url": "Source URL",
    "source_name": "Source name",
    "published_at": "YYYY-MM-DD if available",
    "relevance": "HIGH/MED/LOW",
    "impact_area": "market_structure|supply_chain|demand|technology|labor",
    "impact_direction": "RISK|OPPORTUNITY|NEUTRAL",
    "affected_scope": "Description of which companies/segments affected"
  }}
]

# Quality Filter
- Focus on events impacting MULTIPLE companies, not single-company news
- Quantify market impact where possible (market size, growth rates)
- Korean sources: 산업통상자원부, 업종별 협회, 한국은행 산업동향
- Exclude: Single company earnings (unless industry bellwether), stock price movements without fundamental cause

Return [] if no relevant news found."""

        events = await self._call_perplexity_async(client, prompt, "industry")

        # Tag as INDUSTRY
        for event in events:
            event["event_category"] = "INDUSTRY"

        return events

    async def _search_environment_events_async(
        self,
        client: httpx.AsyncClient,
        industry_name: str,
        industry_code: str,
        selected_queries: list[str],
    ) -> list[dict]:
        """Async version of ENVIRONMENT search."""
        today = datetime.now().strftime("%Y-%m-%d")

        # Build targeted queries based on profile
        query_topics = []

        if selected_queries:
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
                f"{industry_name} 정책 규제 변경 정부 발표",
                f"{industry_name} 세제 혜택 보조금 지원",
                f"{industry_name} 환율 금리 영향 수출",
            ]

        query_focus = "\n".join(f"- {topic}" for topic in query_topics)

        prompt = f"""# Search Context
Target Industry: {industry_name} (code: {industry_code})
Time Window: Last 30 days
Today's date: {today}

# Focused Search Topics
{query_focus}

# Search Objectives
Find policy, regulation, and macro-economic news:

## 1. Government Policy
- New policies or regulations affecting this industry
- Implementation timeline and scope
- Enforcement actions or penalties

## 2. Fiscal & Tax
- Tax changes, subsidies, or incentives
- Budget allocations for industry support
- Tariff changes

## 3. Trade & Geopolitics
- Trade policy changes (FTA, export controls)
- Geopolitical tensions affecting supply chains
- Sanctions or trade restrictions

## 4. Environmental & ESG
- Carbon regulations, emission standards
- ESG disclosure requirements
- Green taxonomy impacts

## 5. Monetary & Financial
- Interest rate impacts on industry
- Exchange rate volatility effects
- Credit market conditions

# Output Requirements
Return results as JSON array:
[
  {{
    "title": "Event title (Korean)",
    "headline": "15자 이내 핵심 요약",
    "summary": "Brief summary explaining policy/regulatory impact (100자 이내)",
    "source_url": "Source URL",
    "source_name": "Source name",
    "published_at": "YYYY-MM-DD if available",
    "relevance": "HIGH/MED/LOW",
    "policy_area": "government|fiscal|trade|environmental|monetary",
    "impact_direction": "RISK|OPPORTUNITY|NEUTRAL",
    "effective_date": "If known, when policy takes effect"
  }}
]

# Quality Filter
- Prioritize: 정부 발표, 관보, 규제기관 공지
- Korean sources: 기획재정부, 산업부, 금융위, 한국은행
- FACT-BASED only (no speculation about future policy)

Return [] if no relevant news found."""

        events = await self._call_perplexity_async(client, prompt, "environment")

        # Tag as ENVIRONMENT
        for event in events:
            event["event_category"] = "ENVIRONMENT"

        return events
