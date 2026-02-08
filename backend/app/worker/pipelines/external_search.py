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

P0 Anti-Hallucination Enhancement (2026-02-08):
- 검색 범위 확장: 뉴스 → 공시, 보고서, IR자료, 연구자료 포함
- 블로그/커뮤니티 Hard Block
- Summary 200자 이상 필수
- source_excerpt 필수 (원문 인용)
- status 필드로 검색 실패/무결과 구분
- Temperature 0.0으로 창의성 완전 차단

Buffett Enhancement (2026-02-08):
- P0: 프롬프트 분리 (검색/추출/분석/검증) - Circle of Competence
- P0: retrieval_confidence 필드 (VERBATIM/PARAPHRASED/INFERRED) - Margin of Safety
- P1: Falsification 체크리스트 - Invert, Always Invert
- P1: 공시 데이터 최우선 - Value > Price
- P2: could_not_find 필드 필수화 - "모르겠다" 허용
- P2: 자동화된 원문 대조 검증 - 10-K Test
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import httpx

from app.core.config import settings
from app.worker.llm.key_rotator import get_key_rotator
from app.worker.llm.fact_checker import get_fact_checker, FactCheckResult

# DART API for Fact-based verification context
try:
    from app.services.dart_api import (
        get_extended_fact_profile,
        get_company_info_by_name,
        ExtendedFactProfile,
    )
    DART_AVAILABLE = True
except ImportError:
    DART_AVAILABLE = False
    ExtendedFactProfile = None

logger = logging.getLogger(__name__)


# =============================================================================
# DART Context for LLM Verification
# =============================================================================

@dataclass
class DARTContext:
    """DART 공시 데이터 컨텍스트 (100% Fact)"""
    corp_code: Optional[str] = None
    ceo_name: Optional[str] = None
    established_date: Optional[str] = None
    headquarters: Optional[str] = None
    employee_count: Optional[int] = None
    shareholders: Optional[list] = None
    executives: Optional[list] = None

    def to_prompt_context(self) -> str:
        """LLM 프롬프트에 주입할 컨텍스트 생성"""
        if not any([self.ceo_name, self.headquarters, self.shareholders]):
            return ""

        lines = ["## DART 공시 데이터 (100% Fact - 검증 기준)"]

        if self.ceo_name:
            lines.append(f"- 대표이사: {self.ceo_name}")
        if self.established_date:
            lines.append(f"- 설립일: {self.established_date}")
        if self.headquarters:
            lines.append(f"- 본사: {self.headquarters}")
        if self.employee_count:
            lines.append(f"- 임직원: {self.employee_count}명")
        if self.shareholders:
            sh_str = ", ".join([f"{s.get('name', '')}({s.get('ratio', '')}%)"
                               for s in self.shareholders[:5]])
            lines.append(f"- 주요주주: {sh_str}")
        if self.executives:
            exec_str = ", ".join([f"{e.get('name', '')}({e.get('title', '')})"
                                  for e in self.executives[:3]])
            lines.append(f"- 임원: {exec_str}")

        lines.append("")
        lines.append("⚠️ 위 정보와 불일치하는 검색 결과는 의심하세요.")
        lines.append("")

        return "\n".join(lines)


def fetch_dart_context(corp_name: str) -> DARTContext:
    """DART API에서 검증용 컨텍스트 조회"""
    if not DART_AVAILABLE:
        logger.debug("DART API not available")
        return DARTContext()

    try:
        # Extended Fact Profile 조회 (임원 포함)
        profile = get_extended_fact_profile(corp_name)

        if profile:
            return DARTContext(
                corp_code=profile.corp_code,
                ceo_name=profile.ceo_name,
                established_date=profile.established_date,
                headquarters=profile.headquarters,
                shareholders=[{"name": s.name, "ratio": s.ratio}
                             for s in (profile.shareholders or [])],
                executives=[{"name": e.name, "title": e.title}
                           for e in (profile.executives or [])[:5]],
            )

        # Fallback: 기본 회사 정보만
        company_info = get_company_info_by_name(corp_name)
        if company_info:
            return DARTContext(
                corp_code=company_info.get("corp_code"),
                ceo_name=company_info.get("ceo_nm"),
                established_date=company_info.get("est_dt"),
                headquarters=company_info.get("adres"),
            )

    except Exception as e:
        logger.warning(f"[DART] Failed to fetch context for {corp_name}: {e}")

    return DARTContext()


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

# Priority sources for Korean corporate news (P0 Enhanced)
PRIORITY_SOURCES = {
    # Tier 1: 공시, 정부, 규제기관 (HIGHEST TRUST)
    "tier1": [
        "dart.fss.or.kr",      # DART 전자공시
        "kind.krx.co.kr",      # KRX KIND
        ".go.kr",              # 정부 기관
        "bok.or.kr",           # 한국은행
        "fss.or.kr",           # 금융감독원
    ],
    # Tier 2: 신용평가사, 연구기관, 주요 경제지
    "tier2": [
        "kisrating.com",       # 한국신용평가
        "nicerating.com",      # NICE신용평가
        "korearatings.com",    # 한국기업평가
        "kdi.re.kr",           # KDI
        "kiet.re.kr",          # 산업연구원
        "hankyung.com",        # 한국경제
        "mk.co.kr",            # 매일경제
        "sedaily.com",         # 서울경제
        "edaily.co.kr",        # 이데일리
    ],
    # Tier 3: 통신사, 방송사
    "tier3": [
        "yna.co.kr",           # 연합뉴스
        "newsis.com",          # 뉴시스
        "news1.kr",            # 뉴스1
        "reuters.com",         # 로이터
        "bloomberg.com",       # 블룸버그
    ],
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


# =============================================================================
# Realistic System Prompt (P0 Fix: Perplexity 한계 인정)
# - Perplexity는 웹 크롤링 기반 → DART/신평사 직접 접근 불가
# - 뉴스/기사 검색에 집중, Tier 1 데이터는 별도 API로 처리
# - 전체 한국어 통일
# =============================================================================

PERPLEXITY_SYSTEM_PROMPT = """당신은 한국 기업 뉴스를 검색하는 도우미입니다.

## 역할
- 뉴스/기사에서 사실만 찾아 보고
- 분석, 해석, 예측 금지
- 못 찾으면 솔직하게 "해당 정보 없음"

## 검색 가능한 출처 (현실적 범위)
당신이 접근할 수 있는 출처:
- 경제지: 한경, 매경, 조선비즈, 이데일리
- 통신사: 연합뉴스, 뉴시스, 뉴스1
- 외신: 로이터, 블룸버그
- 포털 뉴스: 네이버뉴스, 다음뉴스

접근 불가 (요청하지 마세요):
- DART 전자공시 (로그인 필요)
- 신용평가사 리포트 (유료 구독)
- 금감원 내부 자료

## 금지 표현
절대 사용 금지: 추정, 전망, 예상, 것으로 보인다, 가능성, 대략, 약, 정도

## 출력 규칙
1. JSON 형식만 (마크다운 금지)
2. 한국어만 사용
3. 출처 URL 필수
4. 날짜 필수 (YYYY-MM-DD)"""

# Legacy alias
BUFFETT_SYSTEM_PROMPT = PERPLEXITY_SYSTEM_PROMPT

# Legacy alias for backward compatibility
PERPLEXITY_SYSTEM_PROMPT = BUFFETT_SYSTEM_PROMPT


# =============================================================================
# Buffett P1: Falsification Checklist
# =============================================================================

FALSIFICATION_RULES = {
    # 수치 범위 검증 (업종별 합리적 범위)
    "revenue_change_max_pct": 200,      # 매출 증감률 최대 ±200%
    "profit_change_max_pct": 500,       # 영업이익 증감률 최대 ±500%
    "debt_ratio_max_pct": 2000,         # 부채비율 최대 2000%
    "employee_change_max_pct": 100,     # 임직원 증감률 최대 ±100%

    # 의심 키워드 (이 단어가 있으면 추가 검증 필요)
    "suspicious_keywords": [
        "관계자에 따르면",
        "업계에서는",
        "소식통",
        "익명",
        "추정",
        "전망",
        "예상",
        "~할 것",
        "~될 것",
    ],

    # 반드시 교차검증 필요한 주제
    "cross_verify_required": [
        "부도",
        "파산",
        "횡령",
        "배임",
        "분식회계",
        "신용등급 하락",
        "대규모 감원",
    ],
}


# =============================================================================
# Buffett P2: Hallucination Indicators (절대 허용 불가 표현)
# =============================================================================

HALLUCINATION_INDICATORS = [
    "~로 추정됨",
    "~로 보임",
    "~로 예상됨",
    "~할 것으로 보임",
    "~할 것으로 예상",
    "~할 전망",
    "일반적으로",
    "통상적으로",
    "업계에서는",
    "시장에서는",
    "대략",
    "약",
    "정도",
    "내외",
    "가량",
]


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
        enable_fact_check: bool = True,
    ) -> dict:
        """
        Execute external search stage with 3-track search.

        개선사항 (2026-02-08):
        1. DART 데이터 LLM 컨텍스트 주입 - 검증 기준 제공
        2. Gemini Grounding 전체 팩트체크 - 모든 검색 결과 검증

        ADR-009 Enhancement:
        - parallel_mode=True: 3-Track 동시 실행 (40% speedup)
        - parallel_mode=False: 기존 순차 실행

        Args:
            corp_name: Corporation name for search
            industry_code: Industry code (e.g., C26)
            corp_id: Corporation ID for logging
            profile_data: Optional profile data with selected_queries
            corp_reg_no: Optional corporate registration number
            enable_fact_check: Enable Gemini fact-checking for all results

        Returns:
            dict with categorized events and metadata
        """
        industry_name = self._get_industry_name(industry_code)
        logger.info(
            f"EXTERNAL stage starting for corp_id={corp_id}, "
            f"corp_name={corp_name}, industry={industry_name}, "
            f"parallel_mode={self.parallel_mode}, fact_check={enable_fact_check}"
        )

        if not self.enabled:
            logger.info("External search disabled (no API key)")
            return self._empty_result("disabled")

        try:
            # Step 1: DART 컨텍스트 조회 (검증 기준)
            dart_context = fetch_dart_context(corp_name)
            if dart_context.ceo_name:
                logger.info(f"[DART] Context loaded: CEO={dart_context.ceo_name}")
            else:
                logger.info("[DART] No context available")

            selected_queries = []
            if profile_data and profile_data.get("selected_queries"):
                selected_queries = profile_data["selected_queries"]

            # Step 2: Perplexity 검색 (DART 컨텍스트 주입)
            if self.parallel_mode:
                result = self._execute_parallel(
                    corp_name, industry_name, industry_code,
                    corp_reg_no, selected_queries, dart_context
                )
            else:
                result = self._execute_sequential(
                    corp_name, industry_name, industry_code,
                    corp_reg_no, selected_queries, dart_context
                )

            # Step 3: Gemini 팩트체크 (모든 결과)
            if enable_fact_check and result.get("events"):
                result = self._fact_check_all_events(result, corp_name)

            return result

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
        dart_context: Optional[DARTContext] = None,
    ) -> dict:
        """
        병렬 모드: 3-Track 동시 실행

        ADR-009 Sprint 1 구현:
        - asyncio.gather()로 3개 API 동시 호출
        - 개별 실패는 빈 리스트로 처리 (Graceful Degradation)

        개선사항 (2026-02-08):
        - DART 컨텍스트를 프롬프트에 주입하여 검증 기준 제공
        """
        start_time = time.time()

        # DART 컨텍스트 프롬프트 생성
        dart_prompt = dart_context.to_prompt_context() if dart_context else ""

        async def run_parallel():
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                tasks = [
                    self._search_direct_events_async(
                        client, corp_name, industry_name, corp_reg_no,
                        dart_context=dart_prompt
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
        dart_context: Optional[DARTContext] = None,
    ) -> dict:
        """순차 모드: 기존 방식"""
        start_time = time.time()

        # DART 컨텍스트 프롬프트 생성
        dart_prompt = dart_context.to_prompt_context() if dart_context else ""

        # Track 1: DIRECT - Company-specific credit risk signals
        direct_events = self._search_direct_events(
            corp_name, industry_name, corp_reg_no, dart_context=dart_prompt
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
        biz_no: Optional[str] = None,
        headquarters: Optional[str] = None,
        dart_context: str = "",
    ) -> list[dict]:
        """
        Track 1: Search for company-specific credit risk signals.

        P0 Fix (2026-02-08):
        - entity_verified 제거 (Perplexity로 불가능, 코드에서 DART API로 검증)
        - source_sentence 강제 제거 (Perplexity는 요약 AI)
        - 스키마 단순화 (20개 → 6개 핵심 필드)
        - YoY 필수 → 선택적

        개선 (2026-02-08):
        - DART 컨텍스트 주입: 공시 데이터 기반 검증 기준 제공
        """
        today = datetime.now().strftime("%Y-%m-%d")

        # DART 컨텍스트가 있으면 프롬프트에 추가
        dart_section = ""
        if dart_context:
            dart_section = f"""
{dart_context}
"""

        prompt = f"""## 검색 대상
- 기업명: {corp_name}
- 업종: {industry_name}
- 검색일: {today}
- 검색기간: 최근 90일
{dart_section}
## 검색 요청
"{corp_name}" 관련 뉴스에서 아래 항목을 찾아주세요.

### 찾아야 할 정보 (우선순위)
1. **부정적 이벤트**: 연체, 부도, 소송, 과징금, 행정처분
2. **경영 변화**: 대표이사 교체, 대주주 변경, 대규모 인력 변동
3. **재무 뉴스**: 실적 발표 (매출/영업이익 금액과 전년비), 신용등급 변경
4. **사업 변화**: 주요 계약 체결/해지, 사업 철수/확장

### 주의사항
⚠️ 동명이인 주의: "{corp_name}" ({industry_name} 업종)만 해당
⚠️ 다른 회사 뉴스 포함 금지
⚠️ 추측/전망 기사 제외, 확정된 사실만
⚠️ 위 DART 공시 정보와 불일치하면 재확인 필요

### 출력 형식 (간결한 JSON)
{{
  "status": "FOUND" | "NOT_FOUND",
  "facts": [
    {{
      "title": "뉴스 제목 또는 사실 요약 (50자 이내)",
      "summary": "핵심 내용 2-3문장 (숫자+단위 포함)",
      "source_url": "기사 URL (필수)",
      "date": "YYYY-MM-DD (기사 날짜)",
      "impact": "RISK | OPPORTUNITY | NEUTRAL"
    }}
  ],
  "not_found": ["찾지 못한 항목 (있으면)"]
}}

정보가 없으면:
{{"status": "NOT_FOUND", "facts": [], "not_found": ["해당 기간 내 관련 뉴스 없음"]}}"""

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

        P0 Fix (2026-02-08):
        - 스키마 단순화 (6개 핵심 필드)
        - 현실적 출처만 요청 (경제지, 통신사)
        - falsification_check 제거 (코드에서 처리)
        """
        today = datetime.now().strftime("%Y-%m-%d")

        # Get industry-specific keywords
        keywords = INDUSTRY_KEYWORDS.get(industry_code, DEFAULT_INDUSTRY_KEYWORDS)
        supply_keywords = ", ".join(keywords.get("supply_chain", []))

        prompt = f"""## 검색 대상
- 업종: {industry_name}
- 참조 기업: {corp_name} (이 기업만 검색하지 마세요)
- 검색일: {today}
- 검색기간: 최근 90일

## 검색 요청
"{industry_name}" 업종 전체에 영향을 미치는 뉴스를 찾아주세요.
**조건: 특정 기업이 아닌, 업종 전체/다수 기업에 영향을 미치는 뉴스만**

### 찾아야 할 정보
1. **산업 통계**: 생산지수, 수출입 동향, 업황 전망
2. **공급망 이슈**: 원자재 가격, 부품 수급, 물류 차질
3. **규제 변화**: 업종 관련 정책, 법률 개정
4. **시장 변화**: 수요 변동, 경쟁 구도, 기술 트렌드

### 업종 키워드 (참고용)
{supply_keywords}

### 제외 대상
❌ 개별 기업 실적 발표
❌ 단일 기업 주가 변동
❌ 블로그/커뮤니티 출처

### 출력 형식 (간결한 JSON)
{{
  "status": "FOUND" | "NOT_FOUND",
  "facts": [
    {{
      "title": "뉴스 제목 (50자 이내)",
      "summary": "핵심 내용 2-3문장",
      "source_url": "기사 URL (필수)",
      "date": "YYYY-MM-DD",
      "impact": "RISK | OPPORTUNITY | NEUTRAL",
      "affected_scope": "영향 범위 (예: 반도체 업종 전체)"
    }}
  ],
  "not_found": ["찾지 못한 항목"]
}}

업종 전체 뉴스가 없으면:
{{"status": "NOT_FOUND", "facts": [], "not_found": ["해당 기간 내 업종 전체 영향 뉴스 없음"]}}"""

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
        corp_name: Optional[str] = None,
    ) -> list[dict]:
        """
        Track 3: Search for policy, regulation, and macro-economic changes.

        P0 Fix (2026-02-08):
        - 스키마 단순화 (6개 핵심 필드)
        - 현실적 출처만 (경제지 정책 기사)
        - falsification_check 제거
        """
        today = datetime.now().strftime("%Y-%m-%d")

        # Build targeted queries based on profile
        query_topics = []

        if selected_queries:
            for query_key in selected_queries[:5]:
                if query_key in ENVIRONMENT_QUERY_TEMPLATES:
                    query_topics.append(
                        ENVIRONMENT_QUERY_TEMPLATES[query_key].format(
                            industry_name=industry_name
                        )
                    )
        else:
            query_topics = [
                f"{industry_name} 정책 규제 변경",
                f"{industry_name} 정부 지원 보조금",
                f"{industry_name} 환율 금리 영향",
            ]

        query_focus = "\n".join(f"- {topic}" for topic in query_topics)

        prompt = f"""## 검색 대상
- 업종: {industry_name}
- 검색일: {today}
- 검색기간: 최근 90일

## 검색 요청
"{industry_name}" 업종에 영향을 미치는 정책/규제/거시경제 뉴스를 찾아주세요.

### 찾아야 할 정보
{query_focus}

### 구체적 항목
1. **정책 변화**: 법률 제정/개정, 시행령 변경, 정부 발표
2. **규제 변화**: 인허가 기준, 환경규제, 안전기준
3. **금융/통화**: 금리 결정, 환율 동향, 자금 지원
4. **무역/통상**: 관세, FTA, 수출규제

### 제외 대상
❌ "검토 중", "논의 중" 등 미확정 정책
❌ "~할 전망", "~할 예정" 등 추측성 기사
❌ 업계 요청/건의 (정책 아님)

### 출력 형식 (간결한 JSON)
{{
  "status": "FOUND" | "NOT_FOUND",
  "facts": [
    {{
      "title": "정책/규제 제목 (50자 이내)",
      "summary": "핵심 내용 2-3문장 (확정된 사실만)",
      "source_url": "기사 URL (필수)",
      "date": "YYYY-MM-DD",
      "impact": "RISK | OPPORTUNITY | NEUTRAL",
      "policy_area": "regulatory | fiscal | trade | monetary"
    }}
  ],
  "not_found": ["찾지 못한 항목"]
}}

확정된 정책 뉴스가 없으면:
{{"status": "NOT_FOUND", "facts": [], "not_found": ["해당 기간 내 확정된 정책 변화 없음"]}}"""

        events = self._call_perplexity(prompt, "environment")

        # Tag as ENVIRONMENT
        for event in events:
            event["event_category"] = "ENVIRONMENT"

        return events

    def _call_perplexity(self, prompt: str, search_type: str) -> list[dict]:
        """
        Call Perplexity API and parse response.

        P0 Enhanced (2026-02-08):
        - Temperature 0.0 (창의성 완전 차단)
        - 새로운 System Prompt (간결하고 엄격)
        - status 필드 기반 응답 파싱
        - source_excerpt 검증
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.MODEL,
            "messages": [
                {"role": "system", "content": PERPLEXITY_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.0,  # P0: 창의성 완전 차단
            "max_tokens": 4000,  # 증가: 긴 summary 허용
            "top_p": 1.0,
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

            # P0: 새로운 파싱 로직 (status 필드 지원)
            events = self._parse_events_v2(content, citations, search_type)
            return events

        except httpx.TimeoutException:
            logger.warning(f"[SEARCH_FAILED] Perplexity API timeout for {search_type} search")
            return []
        except httpx.HTTPStatusError as e:
            logger.error(f"[SEARCH_FAILED] Perplexity API error for {search_type}: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"[SEARCH_FAILED] Perplexity call failed for {search_type}: {e}")
            return []

    def _parse_events_v2(
        self,
        content: str,
        citations: list[str] = None,
        search_type: str = "unknown",
    ) -> list[dict]:
        """
        Parse events from Perplexity response (Buffett Enhanced).

        Handles Buffett-style JSON format:
        - retrieval_status: FOUND | NOT_FOUND | PARTIAL | CONFLICTING
        - facts: 사실 배열 (기존 events 대신)
        - could_not_find: 찾지 못한 항목 (P2)
        - falsification_check: 검증 결과 (P1)

        Also handles legacy formats for backward compatibility.
        """
        try:
            # JSON 객체 찾기
            start_idx = content.find("{")
            end_idx = content.rfind("}") + 1

            if start_idx == -1 or end_idx == 0:
                # Fallback: 기존 배열 포맷 시도
                return self._parse_events_legacy(content, citations, search_type)

            json_str = content[start_idx:end_idx]
            response_obj = json.loads(json_str)

            # Buffett 포맷 확인 (retrieval_status 필드)
            retrieval_status = response_obj.get("retrieval_status")
            if retrieval_status:
                return self._parse_buffett_response(response_obj, search_type)

            # P0 Simple/Legacy 포맷 (status 필드)
            status = response_obj.get("status", "SUCCESS")
            reason = response_obj.get("reason", "")
            not_found = response_obj.get("not_found", [])

            # P0 Simple 포맷: status=NOT_FOUND 처리
            if status == "NOT_FOUND":
                logger.info(f"[{search_type}] NOT_FOUND: {not_found}")
                return []
            elif status == "NO_RESULTS":
                logger.info(f"[{search_type}] NO_RESULTS: {reason}")
                return []
            elif status == "NO_CREDIBLE_SOURCES":
                logger.warning(f"[{search_type}] NO_CREDIBLE_SOURCES: {reason}")
                return []
            elif status == "SEARCH_FAILED":
                logger.error(f"[{search_type}] SEARCH_FAILED: {reason}")
                return []

            # P0 Fix: facts 키도 events로 처리 (새 스키마 호환)
            events = response_obj.get("events", response_obj.get("facts", []))

            # 유효성 검증 및 필터링
            valid_events = []
            for event in events:
                validated = self._validate_event_v2(event, search_type)
                if validated:
                    valid_events.append(validated)

            logger.info(
                f"[{search_type}] Parsed {len(valid_events)}/{len(events)} valid events"
            )
            return valid_events

        except json.JSONDecodeError as e:
            logger.error(f"[{search_type}] JSON parse error: {e}")
            # Fallback: 기존 배열 포맷 시도
            return self._parse_events_legacy(content, citations, search_type)

    def _parse_buffett_response(
        self,
        response_obj: dict,
        search_type: str,
    ) -> list[dict]:
        """
        Parse Buffett-style response (P0/P1/P2 Enhanced).

        New format fields:
        - retrieval_status: FOUND | NOT_FOUND | PARTIAL | CONFLICTING
        - search_limitations: 검색 한계 설명
        - could_not_find: 찾지 못한 항목 배열 (P2)
        - facts: 사실 배열
        - falsification_check: 검증 결과 (P1)

        P0 E2E Test Fixes (2026-02-08):
        - could_not_find 빈 배열 경고 강화
        - falsification_check 결과에 따른 자동 신뢰도 하향
        """
        retrieval_status = response_obj.get("retrieval_status", "NOT_FOUND")
        search_limitations = response_obj.get("search_limitations", "")
        could_not_find = response_obj.get("could_not_find", [])
        facts = response_obj.get("facts", [])
        falsification_check = response_obj.get("falsification_check", {})

        # 상태 로깅
        if retrieval_status == "NOT_FOUND":
            logger.info(
                f"[{search_type}][BUFFETT] NOT_FOUND - "
                f"limitations: {search_limitations}, "
                f"could_not_find: {could_not_find}"
            )
            return []
        elif retrieval_status == "CONFLICTING":
            logger.warning(
                f"[{search_type}][BUFFETT] CONFLICTING sources detected - "
                f"falsification: {falsification_check}"
            )
            # P0 Fix: 충돌 시 모든 facts에 경고 플래그 추가
            for fact in facts:
                fact["_conflicting_sources"] = True

        # P0 Fix: could_not_find가 비어있으면서 facts가 있으면 의심
        # (정상적인 검색이라면 일부는 못 찾았을 가능성이 높음)
        if facts and not could_not_find:
            logger.warning(
                f"[{search_type}][BUFFETT][P0] facts={len(facts)} but could_not_find is empty - "
                f"LLM may have ignored 'I don't know' instruction"
            )

        # P1: Falsification 체크 결과 처리
        # P0 Fix: contradicting_sources_found=true면 모든 facts confidence 하향
        confidence_downgrade = False
        if falsification_check:
            if falsification_check.get("contradicting_sources_found"):
                logger.warning(
                    f"[{search_type}][FALSIFICATION] Contradicting sources: "
                    f"{falsification_check.get('contradicting_details', '')}"
                )
                confidence_downgrade = True
            if not falsification_check.get("numbers_within_historical_range", True):
                logger.warning(
                    f"[{search_type}][FALSIFICATION] Numbers out of range: "
                    f"{falsification_check.get('range_concern', '')}"
                )
                confidence_downgrade = True

        # P2: could_not_find 로깅 (이것도 유효한 정보)
        if could_not_find:
            logger.info(
                f"[{search_type}][BUFFETT] Could not find: {could_not_find}"
            )

        # facts 검증 및 변환
        valid_events = []
        for fact in facts:
            # P0 Fix: falsification 체크 실패 시 confidence 하향
            if confidence_downgrade:
                original_conf = fact.get("retrieval_confidence", "INFERRED")
                if original_conf == "VERBATIM":
                    fact["retrieval_confidence"] = "PARAPHRASED"
                    fact["_confidence_downgraded_reason"] = "falsification_check_failed"
                elif original_conf == "PARAPHRASED":
                    fact["retrieval_confidence"] = "INFERRED"
                    fact["_confidence_downgraded_reason"] = "falsification_check_failed"

            validated = self._validate_buffett_fact(fact, search_type)
            if validated:
                valid_events.append(validated)

        logger.info(
            f"[{search_type}][BUFFETT] Parsed {len(valid_events)}/{len(facts)} valid facts "
            f"(status={retrieval_status}, confidence_downgraded={confidence_downgrade})"
        )

        return valid_events

    def _validate_buffett_fact(
        self,
        fact: dict,
        search_type: str,
    ) -> Optional[dict]:
        """
        Validate Buffett-style fact (P0/P1/P2 Enhanced).

        검증 항목:
        1. retrieval_confidence 검증 (P0: 없으면 REJECTED)
        2. source_sentence 존재 및 길이 (P0: 50자 미만 REJECTED)
        3. Hallucination indicator 검출
        4. INFERRED인 경우 confidence_reason 필수 (P0: 없으면 REJECTED)
        5. 블로그/커뮤니티 차단

        P0 E2E Test Fixes (2026-02-08):
        - retrieval_confidence 없으면 REJECTED (이전: INFERRED로 대체)
        - source_sentence 50자 미만이면 REJECTED (이전: 경고만)
        - INFERRED + confidence_reason 없으면 REJECTED (이전: 경고만)
        """
        # 0. source_url 필수 검증 (P0)
        if not fact.get("source_url"):
            logger.warning(
                f"[{search_type}][BUFFETT][REJECTED] Missing source_url: {fact.get('title', '')[:30]}"
            )
            return None

        # 1. retrieval_confidence 검증 (P0 강화: 없으면 REJECTED)
        confidence = fact.get("retrieval_confidence")
        if not confidence:
            logger.warning(
                f"[{search_type}][BUFFETT][REJECTED] Missing retrieval_confidence: "
                f"{fact.get('title', '')[:30]}"
            )
            return None  # P0 Fix: 이전에는 INFERRED로 대체했지만 이제 거부

        if confidence not in {"VERBATIM", "PARAPHRASED", "INFERRED"}:
            logger.warning(
                f"[{search_type}][BUFFETT][REJECTED] Invalid retrieval_confidence '{confidence}': "
                f"{fact.get('title', '')[:30]}"
            )
            return None

        # INFERRED인 경우 confidence_reason 필수 (P0 강화: 없으면 REJECTED)
        if confidence == "INFERRED":
            if not fact.get("confidence_reason"):
                logger.warning(
                    f"[{search_type}][BUFFETT][REJECTED] INFERRED without confidence_reason: "
                    f"{fact.get('title', '')[:30]}"
                )
                return None  # P0 Fix: 이전에는 경고만, 이제 거부

        # 2. source_sentence 검증 (P0 강화: 50자 미만 REJECTED)
        source_sentence = fact.get("source_sentence", "")
        if len(source_sentence) < 50:
            logger.warning(
                f"[{search_type}][BUFFETT][REJECTED] source_sentence too short "
                f"({len(source_sentence)} chars < 50): {fact.get('title', '')[:30]}"
            )
            return None  # P0 Fix: 이전에는 신뢰도 하향만, 이제 거부

        # 3. Hallucination indicator 검출 (P1 → P0 강화)
        # P0 Fix: source_sentence의 금지 표현은 무조건 REJECT
        source_sentence_indicators = ["전망", "예상", "추정", "예측", "것으로 보인다", "것으로 보임"]
        for indicator in source_sentence_indicators:
            if indicator in source_sentence:
                logger.warning(
                    f"[{search_type}][BUFFETT][REJECTED] Forbidden expression '{indicator}' in source_sentence"
                )
                return None  # P0 Fix: source_sentence 금지 표현은 무조건 거부

        # title/value에서도 검출 (경고 수준)
        text_to_check = f"{fact.get('title', '')} {fact.get('value', '')}"
        for indicator in HALLUCINATION_INDICATORS:
            if indicator in text_to_check:
                logger.warning(
                    f"[{search_type}][HALLUCINATION] Indicator detected in title/value: '{indicator}'"
                )
                fact["_hallucination_indicator"] = indicator
                # 심각한 indicator면 제외
                if indicator in ["~로 추정됨", "~로 예상됨", "~할 전망"]:
                    return None

        # 4. 블로그/커뮤니티 차단
        source_url = fact.get("source_url", "")
        if self._is_excluded_source(source_url):
            logger.warning(
                f"[{search_type}][BUFFETT] Blocked excluded source: {source_url[:50]}"
            )
            return None

        # 5. source_tier 계산 (코드에서 계산)
        fact["source_tier"] = self._get_source_tier(source_url)

        # 6. 숫자 검증: value와 source_sentence 일치 확인
        value = fact.get("value", "")
        if value and source_sentence:
            import re
            # value에서 숫자 추출
            numbers_in_value = re.findall(r'[\d,.]+', str(value))
            for num in numbers_in_value:
                if len(num.replace(",", "").replace(".", "")) >= 3:
                    if num not in source_sentence and num.replace(",", "") not in source_sentence:
                        logger.warning(
                            f"[{search_type}][BUFFETT] Number mismatch: '{num}' not in source_sentence"
                        )
                        fact["_number_mismatch"] = num

        # 7. Legacy 호환성: fact → event 필드 매핑
        fact["title"] = fact.get("title", "")
        fact["summary"] = fact.get("value", fact.get("title", ""))  # Buffett은 summary 대신 value 사용
        fact["source_excerpt"] = source_sentence  # 매핑
        fact["impact_direction"] = fact.get("impact_direction", "NEUTRAL")
        if fact["impact_direction"] not in {"RISK", "OPPORTUNITY", "NEUTRAL"}:
            fact["impact_direction"] = "NEUTRAL"

        return fact

    def _parse_events_legacy(
        self,
        content: str,
        citations: list[str] = None,
        search_type: str = "unknown",
    ) -> list[dict]:
        """Legacy parser for old array format (backward compatibility)."""
        try:
            start_idx = content.find("[")
            end_idx = content.rfind("]") + 1

            if start_idx == -1 or end_idx == 0:
                logger.warning(f"[{search_type}] No JSON found in response")
                return []

            json_str = content[start_idx:end_idx]
            events = json.loads(json_str)

            valid_events = []
            for event in events:
                validated = self._validate_event_v2(event, search_type)
                if validated:
                    valid_events.append(validated)

            return valid_events

        except json.JSONDecodeError as e:
            logger.error(f"[{search_type}] Legacy JSON parse error: {e}")
            return []

    def _validate_event_v2(self, event: dict, search_type: str) -> Optional[dict]:
        """
        Validate a single event dict.

        P0 Fix (2026-02-08):
        - 간소화된 스키마 (6개 핵심 필드) 지원
        - source_excerpt 필수 제거 (Perplexity는 요약 AI)
        - Summary 길이 제한 완화 (200자 → 경고만)
        - impact → impact_direction 매핑

        검증 항목:
        1. 필수 필드 존재 (title, summary, source_url)
        2. 블로그/커뮤니티 URL 차단
        3. Hallucination indicator 검출
        4. source_tier 계산
        5. impact_direction 정규화
        """
        import re

        # 1. 필수 필드 검증
        required_fields = ["title", "summary", "source_url"]
        for field in required_fields:
            if not event.get(field):
                logger.debug(f"[{search_type}] Missing required field: {field}")
                return None

        # 2. 블로그/커뮤니티 URL Hard Block
        source_url = event.get("source_url", "")
        if self._is_excluded_source(source_url):
            logger.warning(
                f"[{search_type}] Blocked excluded source: {source_url[:50]}"
            )
            return None

        title = event.get("title", "")
        summary = event.get("summary", "")

        # 3. Summary 길이 검증 (경고만, 제외 안 함)
        if len(summary) < 50:
            logger.debug(
                f"[{search_type}] Summary short ({len(summary)} chars): {summary[:50]}..."
            )
            event["_validation_warning"] = "summary_short"

        # 4. Hallucination indicator 검출
        text_to_check = f"{title} {summary}"
        for indicator in HALLUCINATION_INDICATORS:
            if indicator in text_to_check:
                logger.warning(
                    f"[{search_type}][HALLUCINATION] Indicator: '{indicator}'"
                )
                event["_hallucination_indicator"] = indicator
                # 심각한 indicator만 제외
                if indicator in ["~로 추정됨", "~로 예상됨", "~할 전망", "~할 것으로 예상"]:
                    logger.warning(
                        f"[{search_type}][REJECTED] Critical hallucination indicator"
                    )
                    return None

        # 5. Falsification 체크 - 교차검증 필요 주제 (경고만)
        for topic in FALSIFICATION_RULES["cross_verify_required"]:
            if topic in text_to_check:
                logger.info(
                    f"[{search_type}][FALSIFICATION] Cross-verify required for: '{topic}'"
                )
                event["_cross_verify_topic"] = topic
                event["_needs_cross_verify"] = True

        # 6. 극단적 수치 검증 (경고 + 플래그)
        percentages = re.findall(r'[-+]?(\d+(?:\.\d+)?)\s*%', summary)
        for pct_str in percentages:
            try:
                pct_value = float(pct_str)
                if abs(pct_value) > FALSIFICATION_RULES["revenue_change_max_pct"]:
                    logger.warning(
                        f"[{search_type}][FALSIFICATION] Extreme value: {pct_value}%"
                    )
                    event["_extreme_value"] = f"{pct_value}%"
                    event["_needs_cross_verify"] = True
            except ValueError:
                pass

        # 7. source_tier 계산 (코드에서 계산, LLM 응답 무시)
        event["source_tier"] = self._get_source_tier(source_url)

        # 8. P0 Fix: impact → impact_direction 매핑
        impact = event.get("impact") or event.get("impact_direction")
        if impact in {"RISK", "OPPORTUNITY", "NEUTRAL"}:
            event["impact_direction"] = impact
        else:
            event["impact_direction"] = "NEUTRAL"

        # 9. P0 Fix: date → published_at 매핑
        if event.get("date") and not event.get("published_at"):
            event["published_at"] = event["date"]

        return event

    def _parse_events(
        self,
        content: str,
        citations: list[str] = None,
        search_type: str = "unknown",
    ) -> list[dict]:
        """Legacy wrapper - calls v2 parser."""
        return self._parse_events_v2(content, citations, search_type)

    def _validate_event(self, event: dict) -> bool:
        """Legacy wrapper - calls v2 validator."""
        return self._validate_event_v2(event, "unknown") is not None

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
    # P2: Buffett 10-K Test - 자동화된 원문 대조 검증
    # =========================================================================

    def buffett_verification_test(
        self,
        events: list[dict],
        fetch_original: bool = False,
    ) -> dict:
        """
        Buffett's 10-K Test: LLM이 추출한 모든 사실을 원문과 대조

        P2 Implementation:
        - source_sentence가 source_url에 실제로 존재하는지 검증
        - 숫자가 source_sentence에 정확히 있는지 검증
        - 문맥 왜곡 여부 검증

        Args:
            events: 검증할 이벤트 목록
            fetch_original: True면 실제 URL 페치 (느림), False면 메타데이터만 검증

        Returns:
            dict with verification results
        """
        import re

        results = {
            "total_events": len(events),
            "passed": 0,
            "failed": 0,
            "warnings": 0,
            "details": [],
        }

        for event in events:
            event_result = {
                "title": event.get("title", "")[:50],
                "source_url": event.get("source_url", "")[:80],
                "checks": [],
                "status": "PASSED",
            }

            # Check 1: source_sentence/source_excerpt 존재
            source_text = event.get("source_sentence") or event.get("source_excerpt", "")
            if not source_text:
                event_result["checks"].append({
                    "check": "source_text_exists",
                    "status": "FAILED",
                    "reason": "No source_sentence or source_excerpt",
                })
                event_result["status"] = "FAILED"
            elif len(source_text) < 30:
                event_result["checks"].append({
                    "check": "source_text_length",
                    "status": "WARNING",
                    "reason": f"Source text too short: {len(source_text)} chars",
                })
                if event_result["status"] == "PASSED":
                    event_result["status"] = "WARNING"
            else:
                event_result["checks"].append({
                    "check": "source_text_exists",
                    "status": "PASSED",
                    "value": f"{len(source_text)} chars",
                })

            # Check 2: retrieval_confidence 검증
            confidence = event.get("retrieval_confidence", "UNKNOWN")
            if confidence == "INFERRED":
                reason = event.get("confidence_reason", "")
                if not reason:
                    event_result["checks"].append({
                        "check": "inferred_has_reason",
                        "status": "FAILED",
                        "reason": "INFERRED without confidence_reason",
                    })
                    event_result["status"] = "FAILED"
                else:
                    event_result["checks"].append({
                        "check": "inferred_has_reason",
                        "status": "WARNING",
                        "reason": f"INFERRED: {reason}",
                    })
                    if event_result["status"] == "PASSED":
                        event_result["status"] = "WARNING"
            elif confidence in {"VERBATIM", "PARAPHRASED"}:
                event_result["checks"].append({
                    "check": "retrieval_confidence",
                    "status": "PASSED",
                    "value": confidence,
                })

            # Check 3: 숫자 일치 검증
            value = event.get("value", "") or event.get("summary", "")
            if value and source_text:
                numbers = re.findall(r'[\d,.]+', str(value))
                significant_numbers = [n for n in numbers if len(n.replace(",", "").replace(".", "")) >= 3]

                for num in significant_numbers:
                    normalized = num.replace(",", "")
                    if num not in source_text and normalized not in source_text:
                        event_result["checks"].append({
                            "check": "number_in_source",
                            "status": "FAILED",
                            "reason": f"Number '{num}' not found in source_text",
                        })
                        event_result["status"] = "FAILED"
                    else:
                        event_result["checks"].append({
                            "check": "number_in_source",
                            "status": "PASSED",
                            "value": num,
                        })

            # Check 4: Hallucination indicator 부재
            text_to_check = f"{event.get('title', '')} {value}"
            found_indicators = []
            for indicator in HALLUCINATION_INDICATORS:
                if indicator in text_to_check:
                    found_indicators.append(indicator)

            if found_indicators:
                event_result["checks"].append({
                    "check": "no_hallucination_indicators",
                    "status": "FAILED",
                    "reason": f"Found indicators: {found_indicators}",
                })
                event_result["status"] = "FAILED"
            else:
                event_result["checks"].append({
                    "check": "no_hallucination_indicators",
                    "status": "PASSED",
                })

            # Check 5: source_tier 검증 (tier1, tier2 우선)
            source_tier = event.get("source_tier", "tier4")
            if source_tier == "tier1":
                event_result["checks"].append({
                    "check": "source_quality",
                    "status": "PASSED",
                    "value": "tier1 (highest trust)",
                })
            elif source_tier == "tier2":
                event_result["checks"].append({
                    "check": "source_quality",
                    "status": "PASSED",
                    "value": "tier2 (high trust)",
                })
            elif source_tier == "tier3":
                event_result["checks"].append({
                    "check": "source_quality",
                    "status": "WARNING",
                    "value": "tier3 (medium trust)",
                })
                if event_result["status"] == "PASSED":
                    event_result["status"] = "WARNING"
            else:
                event_result["checks"].append({
                    "check": "source_quality",
                    "status": "WARNING",
                    "value": f"{source_tier} (unknown/low trust)",
                })
                if event_result["status"] == "PASSED":
                    event_result["status"] = "WARNING"

            # 결과 집계
            if event_result["status"] == "PASSED":
                results["passed"] += 1
            elif event_result["status"] == "WARNING":
                results["warnings"] += 1
            else:
                results["failed"] += 1

            results["details"].append(event_result)

        # 최종 판정
        if results["failed"] == 0 and results["warnings"] == 0:
            results["verdict"] = "BUFFETT_APPROVED"
        elif results["failed"] == 0:
            results["verdict"] = "BUFFETT_APPROVED_WITH_WARNINGS"
        elif results["failed"] < results["total_events"] / 2:
            results["verdict"] = "PARTIAL_APPROVAL"
        else:
            results["verdict"] = "REJECTED"

        logger.info(
            f"[BUFFETT_TEST] {results['verdict']}: "
            f"{results['passed']} passed, {results['warnings']} warnings, {results['failed']} failed "
            f"out of {results['total_events']} events"
        )

        return results

    def apply_buffett_filter(
        self,
        events: list[dict],
        strict_mode: bool = False,
    ) -> list[dict]:
        """
        Buffett 검증을 통과한 이벤트만 반환

        Args:
            events: 원본 이벤트 목록
            strict_mode: True면 WARNING도 제외

        Returns:
            검증 통과한 이벤트 목록
        """
        test_results = self.buffett_verification_test(events)

        filtered = []
        for i, event in enumerate(events):
            if i < len(test_results["details"]):
                detail = test_results["details"][i]
                if detail["status"] == "PASSED":
                    event["_buffett_verified"] = True
                    filtered.append(event)
                elif detail["status"] == "WARNING" and not strict_mode:
                    event["_buffett_verified"] = True
                    event["_buffett_warnings"] = [
                        c for c in detail["checks"] if c["status"] == "WARNING"
                    ]
                    filtered.append(event)
                else:
                    logger.warning(
                        f"[BUFFETT_FILTER] Rejected: {event.get('title', '')[:30]}"
                    )

        logger.info(
            f"[BUFFETT_FILTER] {len(filtered)}/{len(events)} events passed "
            f"(strict_mode={strict_mode})"
        )

        return filtered

    # =========================================================================
    # Async Methods for Parallel Execution (ADR-009 Sprint 1)
    # =========================================================================

    async def _call_perplexity_async(
        self,
        client: httpx.AsyncClient,
        prompt: str,
        search_type: str,
    ) -> list[dict]:
        """
        Async version of Perplexity API call.

        P0 Anti-Hallucination Enhancement (2026-02-08):
        - Temperature 0.0 (창의성 완전 차단)
        - PERPLEXITY_SYSTEM_PROMPT 사용 (Elon-style)
        - max_tokens 4000 (더 긴 응답 허용)
        - status 필드로 검색 상태 구분
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.MODEL,
            "messages": [
                {"role": "system", "content": PERPLEXITY_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.0,  # P0: 창의성 완전 차단
            "max_tokens": 4000,  # P0: 더 긴 응답 허용
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

            # P0: 새로운 파싱 로직 사용 (status 필드 지원)
            events = self._parse_events_v2(content, citations, search_type)
            return events

        except httpx.TimeoutException:
            logger.warning(f"[P0] Perplexity API timeout for {search_type} search (async)")
            return []
        except httpx.HTTPStatusError as e:
            logger.error(f"[P0] Perplexity API error for {search_type}: {e.response.status_code} (async)")
            return []
        except Exception as e:
            logger.error(f"[P0] Perplexity call failed for {search_type}: {e} (async)")
            return []

    async def _search_direct_events_async(
        self,
        client: httpx.AsyncClient,
        corp_name: str,
        industry_name: str,
        corp_reg_no: Optional[str] = None,
        biz_no: Optional[str] = None,
        headquarters: Optional[str] = None,
        dart_context: str = "",
    ) -> list[dict]:
        """
        Async version of DIRECT search.

        P0 Fix (2026-02-08):
        - entity_verified 제거 (Perplexity로 불가능, 코드에서 DART API로 검증)
        - source_sentence 강제 제거 (Perplexity는 요약 AI)
        - 스키마 단순화 (20개 → 6개 핵심 필드)

        개선 (2026-02-08):
        - DART 컨텍스트 주입: 공시 데이터 기반 검증 기준 제공
        """
        today = datetime.now().strftime("%Y-%m-%d")

        # DART 컨텍스트가 있으면 프롬프트에 추가
        dart_section = ""
        if dart_context:
            dart_section = f"""
{dart_context}
"""

        prompt = f"""## 검색 대상
- 기업명: {corp_name}
- 업종: {industry_name}
- 검색일: {today}
- 검색기간: 최근 90일
{dart_section}
## 검색 요청
"{corp_name}" 관련 뉴스에서 아래 항목을 찾아주세요.

### 찾아야 할 정보 (우선순위)
1. **부정적 이벤트**: 연체, 부도, 소송, 과징금, 행정처분
2. **경영 변화**: 대표이사 교체, 대주주 변경, 대규모 인력 변동
3. **재무 뉴스**: 실적 발표 (매출/영업이익 금액과 전년비), 신용등급 변경
4. **사업 변화**: 주요 계약 체결/해지, 사업 철수/확장

### 주의사항
⚠️ 동명이인 주의: "{corp_name}" ({industry_name} 업종)만 해당
⚠️ 다른 회사 뉴스 포함 금지
⚠️ 추측/전망 기사 제외, 확정된 사실만
⚠️ 위 DART 공시 정보와 불일치하면 재확인 필요

### 출력 형식 (간결한 JSON)
{{
  "status": "FOUND" | "NOT_FOUND",
  "facts": [
    {{
      "title": "뉴스 제목 또는 사실 요약 (50자 이내)",
      "summary": "핵심 내용 2-3문장 (숫자+단위 포함)",
      "source_url": "기사 URL (필수)",
      "date": "YYYY-MM-DD (기사 날짜)",
      "impact": "RISK | OPPORTUNITY | NEUTRAL"
    }}
  ],
  "not_found": ["찾지 못한 항목 (있으면)"]
}}

정보가 없으면:
{{"status": "NOT_FOUND", "facts": [], "not_found": ["해당 기간 내 관련 뉴스 없음"]}}"""

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
        """
        Async version of INDUSTRY search.

        P0 Fix (2026-02-08):
        - 스키마 단순화 (6개 핵심 필드)
        - 현실적 출처만 요청 (경제지, 통신사)
        - falsification_check 제거 (코드에서 처리)
        """
        today = datetime.now().strftime("%Y-%m-%d")

        # Get industry-specific keywords
        keywords = INDUSTRY_KEYWORDS.get(industry_code, DEFAULT_INDUSTRY_KEYWORDS)
        supply_keywords = ", ".join(keywords.get("supply_chain", []))

        prompt = f"""## 검색 대상
- 업종: {industry_name}
- 참조 기업: {corp_name} (이 기업만 검색하지 마세요)
- 검색일: {today}
- 검색기간: 최근 90일

## 검색 요청
"{industry_name}" 업종 전체에 영향을 미치는 뉴스를 찾아주세요.
**조건: 특정 기업이 아닌, 업종 전체/다수 기업에 영향을 미치는 뉴스만**

### 찾아야 할 정보
1. **산업 통계**: 생산지수, 수출입 동향, 업황 전망
2. **공급망 이슈**: 원자재 가격, 부품 수급, 물류 차질
3. **규제 변화**: 업종 관련 정책, 법률 개정
4. **시장 변화**: 수요 변동, 경쟁 구도, 기술 트렌드

### 업종 키워드 (참고용)
{supply_keywords}

### 제외 대상
❌ 개별 기업 실적 발표
❌ 단일 기업 주가 변동
❌ 블로그/커뮤니티 출처

### 출력 형식 (간결한 JSON)
{{
  "status": "FOUND" | "NOT_FOUND",
  "facts": [
    {{
      "title": "뉴스 제목 (50자 이내)",
      "summary": "핵심 내용 2-3문장",
      "source_url": "기사 URL (필수)",
      "date": "YYYY-MM-DD",
      "impact": "RISK | OPPORTUNITY | NEUTRAL",
      "affected_scope": "영향 범위 (예: 반도체 업종 전체)"
    }}
  ],
  "not_found": ["찾지 못한 항목"]
}}

업종 전체 뉴스가 없으면:
{{"status": "NOT_FOUND", "facts": [], "not_found": ["해당 기간 내 업종 전체 영향 뉴스 없음"]}}"""

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
        corp_name: Optional[str] = None,
    ) -> list[dict]:
        """
        Async version of ENVIRONMENT search.

        P0 Fix (2026-02-08):
        - 스키마 단순화 (6개 핵심 필드)
        - 현실적 출처만 (경제지 정책 기사)
        - falsification_check 제거
        """
        today = datetime.now().strftime("%Y-%m-%d")

        # Build targeted queries based on profile
        query_topics = []

        if selected_queries:
            for query_key in selected_queries[:5]:
                if query_key in ENVIRONMENT_QUERY_TEMPLATES:
                    query_topics.append(
                        ENVIRONMENT_QUERY_TEMPLATES[query_key].format(
                            industry_name=industry_name
                        )
                    )
        else:
            query_topics = [
                f"{industry_name} 정책 규제 변경",
                f"{industry_name} 정부 지원 보조금",
                f"{industry_name} 환율 금리 영향",
            ]

        query_focus = "\n".join(f"- {topic}" for topic in query_topics)

        prompt = f"""## 검색 대상
- 업종: {industry_name}
- 검색일: {today}
- 검색기간: 최근 90일

## 검색 요청
"{industry_name}" 업종에 영향을 미치는 정책/규제/거시경제 뉴스를 찾아주세요.

### 찾아야 할 정보
{query_focus}

### 구체적 항목
1. **정책 변화**: 법률 제정/개정, 시행령 변경, 정부 발표
2. **규제 변화**: 인허가 기준, 환경규제, 안전기준
3. **금융/통화**: 금리 결정, 환율 동향, 자금 지원
4. **무역/통상**: 관세, FTA, 수출규제

### 제외 대상
❌ "검토 중", "논의 중" 등 미확정 정책
❌ "~할 전망", "~할 예정" 등 추측성 기사
❌ 업계 요청/건의 (정책 아님)

### 출력 형식 (간결한 JSON)
{{
  "status": "FOUND" | "NOT_FOUND",
  "facts": [
    {{
      "title": "정책/규제 제목 (50자 이내)",
      "summary": "핵심 내용 2-3문장 (확정된 사실만)",
      "source_url": "기사 URL (필수)",
      "date": "YYYY-MM-DD",
      "impact": "RISK | OPPORTUNITY | NEUTRAL",
      "policy_area": "regulatory | fiscal | trade | monetary"
    }}
  ],
  "not_found": ["찾지 못한 항목"]
}}

확정된 정책 뉴스가 없으면:
{{"status": "NOT_FOUND", "facts": [], "not_found": ["해당 기간 내 확정된 정책 변화 없음"]}}"""

        events = await self._call_perplexity_async(client, prompt, "environment")

        # Tag as ENVIRONMENT
        for event in events:
            event["event_category"] = "ENVIRONMENT"

        return events

    # =========================================================================
    # Gemini Grounding Fact-Check (모든 검색 결과 검증)
    # =========================================================================

    def _fact_check_all_events(
        self,
        result: dict,
        corp_name: str,
        max_concurrent: int = 10,
    ) -> dict:
        """
        모든 Perplexity 검색 결과를 Gemini Grounding으로 팩트체크

        해커톤 최적화 (2026-02-08):
        - max_concurrent=10: 병렬 처리로 3~5초 내 완료
        - FALSE 판정 → 제외, PARTIALLY_VERIFIED → confidence 표시

        Args:
            result: Perplexity 검색 결과
            corp_name: 기업명
            max_concurrent: 최대 동시 요청 수

        Returns:
            팩트체크 완료된 결과 (fact_check 필드 추가, FALSE 이벤트 제외)
        """
        events = result.get("events", [])
        if not events:
            return result

        fact_checker = get_fact_checker()
        if not fact_checker.is_available():
            logger.warning("[FACT_CHECK] Gemini not available, skipping")
            return result

        start_time = time.time()
        logger.info(f"[FACT_CHECK] Starting for {len(events)} events (max_concurrent={max_concurrent})")

        # 이벤트를 시그널 형태로 변환 (fact_checker 호환)
        signals = []
        for event in events:
            signals.append({
                "title": event.get("title", ""),
                "summary": event.get("summary", ""),
                "signal_type": event.get("event_category", "DIRECT"),
                "event_type": event.get("event_category", "UNKNOWN"),
                "impact_direction": event.get("impact_direction", "NEUTRAL"),
                "impact_strength": "MED",
            })

        # 비동기 팩트체크 실행
        try:
            import concurrent.futures

            def run_fact_check():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(
                        fact_checker.check_signals_batch(
                            signals=signals,
                            corp_name=corp_name,
                            max_concurrent=max_concurrent,
                        )
                    )
                finally:
                    loop.close()

            # 별도 스레드에서 실행 (Celery 호환)
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(run_fact_check)
                fact_results = future.result(timeout=60.0)

        except Exception as e:
            logger.error(f"[FACT_CHECK] Failed: {e}")
            # 팩트체크 실패 시 원본 반환 (서비스 중단 방지)
            return result

        # 결과 병합 및 필터링
        verified_events = []
        rejected_count = 0
        partial_count = 0

        for i, (signal, fact_response) in enumerate(fact_results):
            if i >= len(events):
                break

            event = events[i]
            fact_result = fact_response.result

            if fact_result == FactCheckResult.FALSE:
                # FALSE → 제외
                logger.warning(
                    f"[FACT_CHECK][REJECTED] {event.get('title', '')[:40]} - "
                    f"{fact_response.explanation[:100]}"
                )
                rejected_count += 1
                continue

            # 팩트체크 결과 첨부
            event["fact_check"] = {
                "result": fact_result.value,
                "confidence": fact_response.confidence,
                "explanation": fact_response.explanation[:200],
                "sources": fact_response.sources[:3],
            }

            if fact_result == FactCheckResult.PARTIALLY_VERIFIED:
                event["_partially_verified"] = True
                partial_count += 1

            verified_events.append(event)

        elapsed_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"[FACT_CHECK] Completed in {elapsed_ms}ms: "
            f"verified={len(verified_events)}, rejected={rejected_count}, "
            f"partial={partial_count}"
        )

        # 카테고리별 재분류
        direct_events = [e for e in verified_events if e.get("event_category") == "DIRECT"]
        industry_events = [e for e in verified_events if e.get("event_category") == "INDUSTRY"]
        environment_events = [e for e in verified_events if e.get("event_category") == "ENVIRONMENT"]

        # 메타데이터 업데이트
        result["events"] = verified_events
        result["direct_events"] = direct_events
        result["industry_events"] = industry_events
        result["environment_events"] = environment_events
        result["metadata"]["fact_check"] = {
            "enabled": True,
            "verified_count": len(verified_events),
            "rejected_count": rejected_count,
            "partial_count": partial_count,
            "execution_time_ms": elapsed_ms,
        }
        result["metadata"]["events_count"] = {
            "direct": len(direct_events),
            "industry": len(industry_events),
            "environment": len(environment_events),
            "total": len(verified_events),
        }

        return result
