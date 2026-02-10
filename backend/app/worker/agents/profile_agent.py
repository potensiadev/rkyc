"""
Profile Agent
외부 정보 기반 기업 프로파일링을 담당하는 Agent

기존 Corp Profiling Pipeline을 Agent 패턴으로 래핑
"""

import logging
from typing import Optional

from app.worker.agents.base import BaseAgent, AgentResult, AgentStatus

logger = logging.getLogger(__name__)


class ProfileAgent(BaseAgent):
    """
    기업 프로파일 Agent

    Perplexity + Gemini 기반 외부 정보 수집 및 프로파일 생성
    기존 CorpProfilingPipeline을 Agent 패턴으로 래핑
    """

    def __init__(self, timeout_seconds: int = 120):
        super().__init__(
            agent_type="ProfileAgent",
            timeout_seconds=timeout_seconds
        )

    async def execute(self, context: dict) -> AgentResult:
        """
        프로파일 생성 실행

        Context 필수 키:
            - corp_name: 기업명
            - corp_id: 기업 ID (신규는 "new-{job_id}")

        Context 선택 키:
            - industry_code: 업종 코드
            - biz_no: 사업자번호
        """
        corp_name = context.get("corp_name")
        corp_id = context.get("corp_id", "unknown")

        if not corp_name or corp_name == "Unknown":
            return self._skipped("corp_name is required for profiling")

        industry_code = context.get("industry_code", "")

        try:
            # CorpProfilingPipeline 사용
            from app.worker.pipelines.corp_profiling import get_corp_profiling_pipeline

            profiling_pipeline = get_corp_profiling_pipeline()

            # 비동기 실행
            profile_result = await profiling_pipeline.execute(
                corp_id=corp_id,
                corp_name=corp_name,
                industry_code=industry_code,
                db_session=None,
                llm_service=None,
            )

            # 결과 변환
            profile_data = {
                "profile": profile_result.profile or {},  # None 대신 빈 dict
                "selected_queries": profile_result.selected_queries,
                "query_details": profile_result.query_details,
                "is_cached": profile_result.is_cached,
            }

            # P0 Fix: profile이 None일 수 있음
            metadata = {
                "confidence": (
                    profile_result.profile.get("profile_confidence", "UNKNOWN")
                    if profile_result.profile else "UNKNOWN"
                ),
                "query_count": len(profile_result.selected_queries),
                "is_cached": profile_result.is_cached,
            }

            return self._success(data=profile_data, metadata=metadata)

        except Exception as e:
            logger.warning(f"[{self.agent_id}] Profiling failed: {e}")
            # 프로파일링 실패는 치명적이지 않음 - 빈 프로파일로 계속 진행
            return self._failed(
                error=str(e)[:200],
                data={
                    "profile": None,
                    "selected_queries": [],
                    "query_details": [],
                    "is_cached": False,
                }
            )


class LightProfileAgent(BaseAgent):
    """
    경량 프로파일 Agent

    전체 프로파일링 대신 핵심 정보만 빠르게 수집
    (해커톤 데모용 - 속도 우선)
    """

    def __init__(self, timeout_seconds: int = 30):
        super().__init__(
            agent_type="LightProfileAgent",
            timeout_seconds=timeout_seconds
        )

    async def execute(self, context: dict) -> AgentResult:
        """
        경량 프로파일 생성

        Perplexity 1회 호출로 기본 정보만 수집
        """
        corp_name = context.get("corp_name")
        if not corp_name or corp_name == "Unknown":
            return self._skipped("corp_name is required")

        try:
            from app.worker.llm.service import get_llm_service

            llm_service = get_llm_service()

            # 단일 Perplexity 쿼리
            query = f"{corp_name} 기업 개요 주요 사업 최근 뉴스"

            # Perplexity 검색 (있으면)
            try:
                from app.worker.pipelines.external import ExternalSearchPipeline
                external = ExternalSearchPipeline()
                search_result = external._search_perplexity(query)
            except Exception:
                search_result = None

            if not search_result:
                return self._skipped("Perplexity search unavailable")

            # LLM으로 구조화
            prompt = f"""
            다음 검색 결과에서 기업 정보를 추출하세요.

            기업명: {corp_name}
            검색 결과:
            {search_result[:3000]}

            JSON 형식으로 응답:
            {{
                "business_summary": "사업 개요 2-3문장",
                "industry": "업종",
                "key_products": ["주요 제품/서비스"],
                "recent_news": ["최근 주요 뉴스 요약"]
            }}
            """

            response = llm_service.generate(prompt)

            # JSON 파싱
            import json
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                profile = json.loads(json_match.group())
            else:
                profile = {"business_summary": response[:500]}

            return self._success(
                data={"profile": profile, "source": "perplexity_light"},
                metadata={"method": "light_profile"}
            )

        except Exception as e:
            logger.warning(f"[{self.agent_id}] Light profiling failed: {e}")
            return self._failed(str(e)[:200])
