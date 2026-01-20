"""
Signal Agent
시그널 추출을 담당하는 Agent

LLM을 사용하여 문서 및 외부 정보에서 Risk/Opportunity 시그널 추출
"""

import logging
from typing import Optional
from uuid import uuid4

from app.worker.agents.base import BaseAgent, AgentResult, AgentStatus

logger = logging.getLogger(__name__)


class SignalAgent(BaseAgent):
    """
    시그널 추출 Agent

    문서 분석 결과와 프로파일 데이터를 기반으로
    Risk/Opportunity/Neutral 시그널을 추출
    """

    def __init__(self, timeout_seconds: int = 90):
        super().__init__(
            agent_type="SignalAgent",
            timeout_seconds=timeout_seconds
        )

    async def execute(self, context: dict) -> AgentResult:
        """
        시그널 추출 실행

        Context 필수 키:
            - corp_info: 기업 기본 정보
            - doc_summaries: 문서 파싱 결과

        Context 선택 키:
            - profile: 외부 프로파일 데이터
            - shareholders: 주주 정보
            - financial_summary: 재무 요약
        """
        corp_info = context.get("corp_info", {})
        doc_summaries = context.get("doc_summaries", {})

        if not corp_info and not doc_summaries:
            return self._failed("No data available for signal extraction")

        try:
            from app.worker.pipelines import SignalExtractionPipeline, ValidationPipeline
            from app.worker.pipelines import deduplicate_within_batch

            # 파이프라인 초기화
            signal_pipeline = SignalExtractionPipeline()
            validation_pipeline = ValidationPipeline()

            # 컨텍스트 구성
            unified_context = self._build_unified_context(context)

            # 시그널 추출
            raw_signals = signal_pipeline.execute(unified_context)

            # 중복 제거 및 검증
            deduped_signals = deduplicate_within_batch(raw_signals)
            validated_signals = validation_pipeline.execute(deduped_signals)

            # 결과 포맷팅
            formatted_signals = [self._format_signal(s) for s in validated_signals]

            # 통계 계산
            stats = self._calculate_stats(formatted_signals)

            return self._success(
                data={
                    "signals": formatted_signals,
                    "stats": stats,
                },
                metadata={
                    "raw_count": len(raw_signals),
                    "validated_count": len(validated_signals),
                    "risk_count": stats["risk"],
                    "opportunity_count": stats["opportunity"],
                }
            )

        except Exception as e:
            logger.error(f"[{self.agent_id}] Signal extraction failed: {e}")
            return self._failed(str(e)[:300])

    def _build_unified_context(self, context: dict) -> dict:
        """Orchestrator 컨텍스트를 Signal Pipeline 형식으로 변환"""
        corp_info = context.get("corp_info", {})

        return {
            "corp_info": corp_info,
            "snapshot": {
                "corp": {
                    "corp_id": context.get("corp_id"),
                    "corp_name": corp_info.get("corp_name"),
                    "biz_no": corp_info.get("biz_no"),
                    "ceo_name": corp_info.get("ceo_name"),
                },
                "credit": {"has_loan": False},
            },
            "documents": context.get("doc_summaries", {}),
            "shareholders": context.get("shareholders", []),
            "financial_summary": context.get("financial_summary"),
            "external_events": [],
            "profile_data": context.get("profile_data", {}),
            "profile": context.get("profile"),
        }

    def _format_signal(self, signal: dict) -> dict:
        """시그널을 API 응답 형식으로 포맷"""
        return {
            "signal_id": signal.get("signal_id") or str(uuid4()),
            "signal_type": signal.get("signal_type", "DIRECT"),
            "event_type": signal.get("event_type", ""),
            "impact_direction": signal.get("impact_direction", "NEUTRAL"),
            "impact_strength": signal.get("impact_strength", "MED"),
            "confidence": signal.get("confidence", "MED"),
            "title": signal.get("title", ""),
            "summary": signal.get("summary", ""),
            "evidences": signal.get("evidences", []),
        }

    def _calculate_stats(self, signals: list) -> dict:
        """시그널 통계 계산"""
        return {
            "total": len(signals),
            "risk": sum(1 for s in signals if s.get("impact_direction") == "RISK"),
            "opportunity": sum(1 for s in signals if s.get("impact_direction") == "OPPORTUNITY"),
            "neutral": sum(1 for s in signals if s.get("impact_direction") == "NEUTRAL"),
            "high_impact": sum(1 for s in signals if s.get("impact_strength") == "HIGH"),
        }


class DocumentSignalAgent(BaseAgent):
    """
    문서 기반 시그널 추출 Agent

    특정 문서 타입에서 시그널을 추출하는 특화 Agent
    (병렬 처리 시 문서별로 독립적으로 실행 가능)
    """

    def __init__(self, doc_type: str, timeout_seconds: int = 60):
        super().__init__(
            agent_type=f"DocumentSignalAgent-{doc_type}",
            timeout_seconds=timeout_seconds
        )
        self.doc_type = doc_type

    async def execute(self, context: dict) -> AgentResult:
        """문서별 시그널 추출"""
        doc_data = context.get("doc_summaries", {}).get(self.doc_type)
        if not doc_data:
            return self._skipped(f"No data for {self.doc_type}")

        try:
            signals = await self._extract_from_document(doc_data, context)
            return self._success(
                data={"signals": signals, "doc_type": self.doc_type},
                metadata={"signal_count": len(signals)}
            )
        except Exception as e:
            return self._failed(str(e)[:200])

    async def _extract_from_document(self, doc_data: dict, context: dict) -> list:
        """문서 타입별 시그널 추출 로직"""
        from app.worker.llm.service import get_llm_service

        llm_service = get_llm_service()
        corp_name = context.get("corp_info", {}).get("corp_name", "해당 기업")

        # 문서 타입별 프롬프트
        prompts = {
            "BIZ_REG": f"""
                사업자등록증 분석 결과에서 주의할 시그널을 추출하세요.
                기업명: {corp_name}
                데이터: {doc_data}

                확인 사항:
                - 설립일이 최근 1년 이내인지 (신생기업 리스크)
                - 업종/업태 변경 이력
                - 본점 소재지 이전 이력
            """,
            "FINANCIAL": f"""
                재무제표 분석 결과에서 Risk/Opportunity 시그널을 추출하세요.
                기업명: {corp_name}
                데이터: {doc_data}

                확인 사항:
                - 부채비율 200% 이상 (RISK)
                - 매출 성장률 (OPPORTUNITY/RISK)
                - 영업이익률 변화
                - 자본잠식 여부
            """,
            "SHAREHOLDERS": f"""
                주주명부에서 지배구조 관련 시그널을 추출하세요.
                기업명: {corp_name}
                데이터: {doc_data}

                확인 사항:
                - 최대주주 지분율 변화
                - 특수관계인 지분 합계
                - 외국인 지분율
            """,
            "REGISTRY": f"""
                등기부등본에서 법적/지배구조 시그널을 추출하세요.
                기업명: {corp_name}
                데이터: {doc_data}

                확인 사항:
                - 임원 변경 이력 (잦은 변경은 RISK)
                - 자본금 변동 이력
                - 목적사업 변경
            """,
        }

        prompt = prompts.get(self.doc_type)
        if not prompt:
            return []

        response_prompt = prompt + """

        JSON 배열로 응답 (최대 3개):
        [
            {
                "signal_type": "DIRECT",
                "event_type": "FINANCIAL_STATEMENT_UPDATE",
                "impact_direction": "RISK|OPPORTUNITY|NEUTRAL",
                "impact_strength": "HIGH|MED|LOW",
                "confidence": "HIGH|MED|LOW",
                "title": "시그널 제목",
                "summary": "시그널 설명 (2-3문장)",
                "evidences": [{"evidence_type": "DOC", "ref_type": "DOC_PAGE", "ref_value": "추출 근거"}]
            }
        ]
        """

        response = llm_service.generate(response_prompt)

        # JSON 파싱
        import json
        import re
        json_match = re.search(r'\[[\s\S]*\]', response)
        if json_match:
            try:
                signals = json.loads(json_match.group())
                return signals if isinstance(signals, list) else []
            except json.JSONDecodeError:
                return []

        return []
