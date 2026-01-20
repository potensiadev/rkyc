"""
Insight Agent
종합 인사이트 생성을 담당하는 Agent

모든 분석 결과를 종합하여 KYC 인사이트 생성
"""

import logging
from typing import Optional

from app.worker.agents.base import BaseAgent, AgentResult, AgentStatus

logger = logging.getLogger(__name__)


class InsightAgent(BaseAgent):
    """
    인사이트 생성 Agent

    시그널 분석 결과와 기업 정보를 종합하여
    금융기관 심사 담당자를 위한 인사이트 생성
    """

    def __init__(self, timeout_seconds: int = 60):
        super().__init__(
            agent_type="InsightAgent",
            timeout_seconds=timeout_seconds
        )

    async def execute(self, context: dict) -> AgentResult:
        """
        인사이트 생성 실행

        Context 필수 키:
            - signals: 추출된 시그널 목록
            - corp_info: 기업 정보

        Context 선택 키:
            - profile: 외부 프로파일
            - financial_summary: 재무 요약
        """
        signals = context.get("signals", [])
        corp_info = context.get("corp_info", {})

        if not signals:
            return self._success(
                data={
                    "insight": "분석된 시그널이 없습니다. 추가 서류를 제출하시면 더 정확한 분석이 가능합니다.",
                    "summary": {"total": 0, "risk": 0, "opportunity": 0},
                },
                metadata={"method": "empty_fallback"}
            )

        try:
            insight_text = await self._generate_insight(signals, corp_info, context)

            # 요약 통계
            summary = {
                "total": len(signals),
                "risk": sum(1 for s in signals if s.get("impact_direction") == "RISK"),
                "opportunity": sum(1 for s in signals if s.get("impact_direction") == "OPPORTUNITY"),
                "neutral": sum(1 for s in signals if s.get("impact_direction") == "NEUTRAL"),
                "high_confidence": sum(1 for s in signals if s.get("confidence") == "HIGH"),
            }

            return self._success(
                data={
                    "insight": insight_text,
                    "summary": summary,
                },
                metadata={
                    "signal_count": len(signals),
                    "method": "llm_generation",
                }
            )

        except Exception as e:
            logger.error(f"[{self.agent_id}] Insight generation failed: {e}")
            # Fallback: 간단한 요약
            fallback = self._generate_fallback_insight(signals, corp_info)
            return self._success(
                data={
                    "insight": fallback,
                    "summary": {"total": len(signals)},
                },
                metadata={"method": "fallback"}
            )

    async def _generate_insight(self, signals: list, corp_info: dict, context: dict) -> str:
        """LLM을 사용한 인사이트 생성"""
        from app.worker.llm.service import get_llm_service

        llm_service = get_llm_service()
        corp_name = corp_info.get("corp_name", "해당 기업")

        # 시그널 요약
        risk_count = sum(1 for s in signals if s.get("impact_direction") == "RISK")
        opp_count = sum(1 for s in signals if s.get("impact_direction") == "OPPORTUNITY")
        neutral_count = len(signals) - risk_count - opp_count

        # 주요 시그널 텍스트
        signal_texts = []
        for s in signals[:5]:
            direction = s.get("impact_direction", "NEUTRAL")
            direction_ko = {"RISK": "리스크", "OPPORTUNITY": "기회", "NEUTRAL": "중립"}.get(direction, "")
            signal_texts.append(f"- [{direction_ko}] {s.get('title', '')}: {s.get('summary', '')[:100]}")

        signal_summary = "\n".join(signal_texts)

        # 프로파일 정보 (있으면)
        profile = context.get("profile") or {}
        profile_text = ""
        if profile:
            profile_text = f"""
            사업 개요: {profile.get('business_summary', 'N/A')[:200]}
            """

        # 재무 정보 (있으면)
        financial = context.get("financial_summary") or {}
        financial_text = ""
        if financial:
            revenue = financial.get("revenue")
            debt_ratio = financial.get("debt_ratio")
            financial_text = f"""
            매출: {f'{revenue:,}원' if revenue else 'N/A'}
            부채비율: {f'{debt_ratio}%' if debt_ratio else 'N/A'}
            """

        prompt = f"""
        당신은 금융기관의 기업심사 AI 어시스턴트입니다.
        신규 법인 KYC 분석 결과를 바탕으로 심사 담당자를 위한 종합 인사이트를 작성하세요.

        ## 기업 정보
        - 기업명: {corp_name}
        - 사업자번호: {corp_info.get('biz_no', 'N/A')}
        - 대표자: {corp_info.get('ceo_name', 'N/A')}
        {profile_text}
        {financial_text}

        ## 분석 결과
        - 총 시그널: {len(signals)}개
        - 리스크: {risk_count}개, 기회: {opp_count}개, 중립: {neutral_count}개

        ## 주요 시그널
        {signal_summary}

        ## 작성 지침
        1. 3-4문장으로 간결하게 작성
        2. 리스크와 기회 요인을 균형있게 언급
        3. 단정적 표현 금지: "~일 것이다", "반드시", "즉시 조치 필요"
        4. 허용 표현 사용: "~로 추정됨", "~가능성 있음", "검토 권고"
        5. 금융기관 심사 담당자 관점에서 유용한 정보 제공

        인사이트:
        """

        insight = llm_service.generate(prompt)

        # 마크다운 제거
        import re
        insight = re.sub(r'^#{1,6}\s*', '', insight, flags=re.MULTILINE)
        insight = re.sub(r'\*\*([^*]+)\*\*', r'\1', insight)

        return insight.strip()

    def _generate_fallback_insight(self, signals: list, corp_info: dict) -> str:
        """LLM 실패 시 Fallback 인사이트"""
        corp_name = corp_info.get("corp_name", "해당 기업")
        risk_count = sum(1 for s in signals if s.get("impact_direction") == "RISK")
        opp_count = sum(1 for s in signals if s.get("impact_direction") == "OPPORTUNITY")

        parts = [f"{corp_name}에 대한 KYC 분석 결과, 총 {len(signals)}개의 시그널이 감지되었습니다."]

        if risk_count > 0:
            parts.append(f"리스크 요인 {risk_count}건이 확인되어 세부 검토가 권고됩니다.")

        if opp_count > 0:
            parts.append(f"긍정적 기회 요인 {opp_count}건도 함께 확인되었습니다.")

        parts.append("상세 시그널 내용을 참고하여 심사에 활용하시기 바랍니다.")

        return " ".join(parts)


class QuickInsightAgent(BaseAgent):
    """
    빠른 인사이트 Agent

    LLM 호출 없이 규칙 기반으로 빠르게 인사이트 생성
    (데모용, 저지연 필요 시)
    """

    def __init__(self, timeout_seconds: int = 10):
        super().__init__(
            agent_type="QuickInsightAgent",
            timeout_seconds=timeout_seconds
        )

    async def execute(self, context: dict) -> AgentResult:
        """규칙 기반 빠른 인사이트 생성"""
        signals = context.get("signals", [])
        corp_info = context.get("corp_info", {})
        corp_name = corp_info.get("corp_name", "해당 기업")

        if not signals:
            insight = f"{corp_name}에 대한 분석 결과, 특별한 주의 시그널이 감지되지 않았습니다."
        else:
            risk_count = sum(1 for s in signals if s.get("impact_direction") == "RISK")
            opp_count = sum(1 for s in signals if s.get("impact_direction") == "OPPORTUNITY")

            if risk_count > opp_count:
                insight = f"{corp_name}에 대해 {len(signals)}개 시그널 중 리스크 요인({risk_count}건)이 다수 감지되었습니다. 세부 검토를 권고드립니다."
            elif opp_count > risk_count:
                insight = f"{corp_name}에 대해 {len(signals)}개 시그널 중 긍정적 기회 요인({opp_count}건)이 다수 확인되었습니다. 성장 잠재력이 있는 것으로 추정됩니다."
            else:
                insight = f"{corp_name}에 대해 {len(signals)}개의 시그널이 분석되었습니다. 리스크와 기회 요인을 균형있게 검토해 주시기 바랍니다."

        return self._success(
            data={
                "insight": insight,
                "summary": {
                    "total": len(signals),
                    "risk": sum(1 for s in signals if s.get("impact_direction") == "RISK"),
                    "opportunity": sum(1 for s in signals if s.get("impact_direction") == "OPPORTUNITY"),
                },
            },
            metadata={"method": "rule_based"}
        )
