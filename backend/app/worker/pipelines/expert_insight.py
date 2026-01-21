"""
Expert Insight Pipeline - Wall Street Quality Analysis
Stage 8 Enhanced: Generate expert-level briefing using 4-Layer Architecture

Integrates with:
- FourLayerAnalysisPipeline for structured analysis
- Null-free policy enforcement
- Evidence-claim linking
- Actionable checklists
"""

import json
import logging
from typing import Optional

from sqlalchemy import text

from app.worker.db import get_sync_db
from app.worker.llm.service import LLMService
from app.worker.llm.prompts_v2 import (
    EXPERT_ANALYSIS_SYSTEM_PROMPT,
    format_insight_prompt_v2,
    get_industry_context,
)
from app.worker.llm.layer_architecture import (
    FourLayerAnalysisPipeline,
    QualityGateOutput,
    NullFreePolicy,
)
from app.worker.llm.exceptions import AllProvidersFailedError
from app.worker.llm.embedding import get_embedding_service, EmbeddingError

logger = logging.getLogger(__name__)


class ExpertInsightPipeline:
    """
    Enhanced Stage 8: Expert-level insight generation

    Features:
    - 4-Layer architecture (Intake → Evidence → Analysis → Quality Gate)
    - Null-free policy enforcement
    - Wall Street quality corporation analysis
    - Detailed impact path analysis
    - Actionable checklists
    - Similar case search
    """

    def __init__(self):
        self.llm = LLMService()
        self.embedding_service = get_embedding_service()
        self.pipeline = FourLayerAnalysisPipeline(self.llm)
        self.null_policy = NullFreePolicy()

    def execute(self, signals: list[dict], context: dict) -> dict:
        """
        Execute expert insight generation stage.

        Args:
            signals: List of validated signal dicts
            context: Unified context from ContextPipeline

        Returns:
            dict with:
                - insight: Generated insight text
                - expert_analysis: Full QualityGateOutput as dict
                - quality_score: Overall quality score
                - validation_status: VALIDATED/DRAFT
        """
        corp_id = context.get("corp_id", "")
        corp_name = context.get("corp_name", "")

        logger.info(f"[EXPERT_INSIGHT] Starting for corp_id={corp_id}")

        # Handle no signals case
        if not signals:
            return {
                "insight": self._generate_no_signals_insight(corp_name),
                "expert_analysis": None,
                "quality_score": 0.0,
                "validation_status": "NO_SIGNALS"
            }

        # Add signals to context for 4-layer pipeline
        context["signals"] = signals

        # Find similar past cases
        similar_cases = self._find_similar_cases(signals)
        if similar_cases:
            context["similar_cases"] = similar_cases
            logger.info(f"Found {len(similar_cases)} similar past cases")

        try:
            # Execute 4-layer analysis pipeline
            output = self.pipeline.execute(context)

            # Generate insight text from output
            insight = self._generate_insight_from_output(output, context, similar_cases)

            # Convert output to dict for serialization
            output_dict = self.pipeline.to_dict(output)

            logger.info(
                f"[EXPERT_INSIGHT] Completed. Quality={output.quality_metrics['overall_quality_score']:.1f}, "
                f"Status={output.output_status}"
            )

            return {
                "insight": insight,
                "expert_analysis": output_dict,
                "quality_score": output.quality_metrics["overall_quality_score"],
                "validation_status": output.output_status
            }

        except AllProvidersFailedError as e:
            logger.error(f"LLM failed for expert insight: {e}")
            return self._generate_fallback_result(signals, corp_name)

        except Exception as e:
            logger.error(f"Expert insight generation failed: {e}")
            return self._generate_fallback_result(signals, corp_name)

    def _generate_insight_from_output(
        self,
        output: QualityGateOutput,
        context: dict,
        similar_cases: list[dict]
    ) -> str:
        """Generate insight text from 4-layer output using LLM."""

        # Build corporation analysis summary
        corp_analysis_summary = self._build_corp_analysis_summary(output)

        # Build signals summary
        signals_summary = self._build_signals_summary(output)

        # Build evidence quality summary
        evidence_quality = self._build_evidence_quality_summary(output)

        # Get industry context
        industry_code = context.get("industry_code", "")
        industry_ctx = get_industry_context(industry_code)

        # Format prompt
        user_prompt = format_insight_prompt_v2(
            corp_name=context.get("corp_name", ""),
            industry_code=industry_code,
            industry_name=context.get("industry_name", ""),
            corp_analysis_summary=corp_analysis_summary,
            signals_summary=signals_summary,
            signal_count=len(output.signal_analyses),
            evidence_quality=evidence_quality
        )

        # Add similar cases
        if similar_cases:
            user_prompt += f"\n\n### 유사 과거 케이스 참고\n{self._build_similar_cases_summary(similar_cases)}"

        # Add industry context
        user_prompt += f"""

### 업종 참고 정보 ({industry_ctx['name']})
- 일반적 마진 범위: {industry_ctx['typical_margin']}
- 일반적 부채비율: {industry_ctx['typical_debt_ratio']}
- 핵심 리스크: {', '.join(industry_ctx['key_risks'][:3])}
"""

        messages = [
            {"role": "system", "content": EXPERT_ANALYSIS_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]

        insight = self.llm.call_with_fallback(
            messages=messages,
            temperature=0.3,
            max_tokens=2000
        )

        return insight.strip()

    def _build_corp_analysis_summary(self, output: QualityGateOutput) -> str:
        """Build corporation analysis summary for prompt."""
        if not output.corporation_analysis:
            return "기업 분석 데이터 없음"

        corp = output.corporation_analysis
        lines = []

        # Business structure
        business = corp.business_structure
        if business.get("core_business"):
            lines.append(f"**사업 구조**: {business.get('core_business')}")

        # Market position
        market = corp.market_position
        if market.get("market_share_range"):
            lines.append(f"**시장 지위**: 점유율 {market.get('market_share_range')}, {market.get('competitive_position', '')}")

        # Financial profile
        financial = corp.financial_profile
        if financial.get("profitability"):
            prof = financial["profitability"]
            lines.append(
                f"**재무 프로필**: 매출 {prof.get('revenue_range_krw', '추정 필요')}, "
                f"추세 {prof.get('revenue_trend', '확인 필요')}"
            )

        # Risk map
        risk = corp.risk_map
        if risk.get("overall_risk_level"):
            lines.append(f"**전체 리스크 수준**: {risk.get('overall_risk_level')}")

        # ESG
        esg = corp.esg_governance
        if esg.get("governance", {}).get("recent_regulatory_risks"):
            risks = esg["governance"]["recent_regulatory_risks"]
            lines.append(f"**최근 규제 리스크**: {', '.join(risks[:2])}")

        return "\n".join(lines) if lines else "상세 분석 진행 중"

    def _build_signals_summary(self, output: QualityGateOutput) -> str:
        """Build signals summary for prompt."""
        if not output.signal_analyses:
            return "감지된 시그널 없음"

        lines = []

        # Group by direction
        risk_signals = [s for s in output.signal_analyses
                       if s.impact_summary.get("overall_direction") == "RISK"]
        opp_signals = [s for s in output.signal_analyses
                      if s.impact_summary.get("overall_direction") == "OPPORTUNITY"]

        # Opportunities first
        if opp_signals:
            lines.append(f"## 기회 시그널 ({len(opp_signals)}건)")
            for s in opp_signals:
                impact = s.impact_summary
                lines.append(
                    f"- [{impact.get('overall_strength', 'MED')}] {s.event_type}: "
                    f"{impact.get('primary_concern', '')[:80]}"
                )
                # Add key impact path
                if s.impact_paths:
                    path = s.impact_paths[0]
                    lines.append(f"  → 영향 경로: {path.get('path', '')} ({path.get('timeline', '')})")

        # Risk signals
        if risk_signals:
            lines.append(f"\n## 리스크 시그널 ({len(risk_signals)}건)")
            for s in risk_signals:
                impact = s.impact_summary
                lines.append(
                    f"- [{impact.get('overall_strength', 'MED')}] {s.event_type}: "
                    f"{impact.get('primary_concern', '')[:80]}"
                )
                # Add recommended stance
                lines.append(f"  → 권고 대응: {impact.get('recommended_stance', '모니터링')}")

        # Add actionable checks count
        total_checks = sum(len(s.actionable_checks) for s in output.signal_analyses)
        if total_checks > 0:
            lines.append(f"\n**실행 체크리스트**: 총 {total_checks}개 액션 아이템")

        return "\n".join(lines)

    def _build_evidence_quality_summary(self, output: QualityGateOutput) -> str:
        """Build evidence quality summary."""
        if not output.evidence_map:
            return "근거 데이터 없음"

        quality = output.evidence_map.quality_metrics
        cross_ver = output.evidence_map.cross_verification_summary

        lines = [
            f"- 근거 신뢰도 분포: A등급 {quality.get('grade_a_count', 0)}건, "
            f"B등급 {quality.get('grade_b_count', 0)}건, C등급 {quality.get('grade_c_count', 0)}건",
            f"- 평균 신뢰도 점수: {quality.get('average_credibility_score', 0):.1f}/3.0",
            f"- 교차 검증률: {cross_ver.get('verification_rate', 0):.0%}",
            f"- 반대 근거 포함: {'예' if output.evidence_map.counter_evidence else '아니오'}"
        ]

        return "\n".join(lines)

    def _find_similar_cases(
        self,
        signals: list[dict],
        limit: int = 5,
        similarity_threshold: float = 0.7
    ) -> list[dict]:
        """Find similar past cases using embedding similarity."""
        if not signals or not self.embedding_service.is_available:
            return []

        # Use most significant signal
        high_impact = [s for s in signals if s.get("impact_strength") == "HIGH"]
        target_signal = high_impact[0] if high_impact else signals[0]

        combined_text = f"""
Signal Type: {target_signal.get('signal_type', '')}
Event Type: {target_signal.get('event_type', '')}
Title: {target_signal.get('title', '')}
Summary: {target_signal.get('summary', '')}
""".strip()

        try:
            embedding = self.embedding_service.embed_text(combined_text)
            if not embedding:
                return []

            embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

            with get_sync_db() as db:
                result = db.execute(
                    text("""
                        SELECT
                            case_id,
                            corp_id,
                            industry_code,
                            signal_type,
                            event_type,
                            summary,
                            1 - (embedding <=> CAST(:embedding AS vector)) AS similarity
                        FROM rkyc_case_index
                        WHERE embedding IS NOT NULL
                          AND 1 - (embedding <=> CAST(:embedding AS vector)) >= :threshold
                        ORDER BY embedding <=> CAST(:embedding AS vector)
                        LIMIT :limit
                    """),
                    {"embedding": embedding_str, "threshold": similarity_threshold, "limit": limit}
                )

                cases = []
                for row in result:
                    cases.append({
                        "case_id": str(row.case_id),
                        "corp_id": row.corp_id,
                        "industry_code": row.industry_code,
                        "signal_type": row.signal_type,
                        "event_type": row.event_type,
                        "summary": row.summary,
                        "similarity": round(row.similarity, 3)
                    })
                return cases

        except EmbeddingError as e:
            logger.warning(f"Embedding failed for case search: {e}")
            return []
        except Exception as e:
            logger.warning(f"Similar case search failed: {e}")
            return []

    def _build_similar_cases_summary(self, cases: list[dict]) -> str:
        """Build similar cases summary text."""
        if not cases:
            return ""

        lines = []
        for i, case in enumerate(cases, 1):
            similarity_pct = int(case.get("similarity", 0) * 100)
            lines.append(
                f"{i}. [{case.get('signal_type', '')}] {case.get('event_type', '')} "
                f"(유사도 {similarity_pct}%)\n"
                f"   - 업종: {case.get('industry_code', '')}\n"
                f"   - 요약: {case.get('summary', '')[:100]}..."
            )
        return "\n".join(lines)

    def _generate_no_signals_insight(self, corp_name: str) -> str:
        """Generate insight when no signals detected."""
        return (
            f"## {corp_name} 분석 결과\n\n"
            f"**상태**: 새로운 시그널이 발견되지 않았습니다.\n\n"
            f"**평가**:\n"
            f"- 현재 기준으로 특별한 리스크 요인 및 기회 요인은 관찰되지 않음\n"
            f"- 기존 여신 관계 유지 권고\n\n"
            f"**권고 사항**:\n"
            f"- 정기적인 모니터링 계속\n"
            f"- 다음 정기 리뷰 시점에 재분석 권고"
        )

    def _generate_fallback_result(self, signals: list[dict], corp_name: str) -> dict:
        """Generate fallback result when LLM fails."""
        risk_count = sum(1 for s in signals if s.get("impact_direction") == "RISK")
        opp_count = sum(1 for s in signals if s.get("impact_direction") == "OPPORTUNITY")
        high_count = sum(1 for s in signals if s.get("impact_strength") == "HIGH")

        insight_parts = [
            f"## {corp_name} 분석 결과 (간략 버전)\n",
            f"**감지된 시그널**: 총 {len(signals)}건\n"
        ]

        if opp_count > 0:
            insight_parts.append(f"- 기회 시그널: {opp_count}건 (성장/투자/실적개선 기회)")
        if risk_count > 0:
            insight_parts.append(f"- 리스크 시그널: {risk_count}건")
        if high_count > 0:
            insight_parts.append(f"- HIGH 강도: {high_count}건 (우선 검토 필요)")

        insight_parts.append("\n**권고**: 상세 시그널 목록 확인 및 담당자 리뷰 필요")

        return {
            "insight": "\n".join(insight_parts),
            "expert_analysis": None,
            "quality_score": 0.0,
            "validation_status": "FALLBACK"
        }


# =============================================================================
# Helper Functions for External Use
# =============================================================================

def generate_actionable_checklist(output: QualityGateOutput) -> list[dict]:
    """
    Extract actionable checklist from expert analysis output.

    Returns list of action items grouped by priority.
    """
    if not output or not output.signal_analyses:
        return []

    all_checks = []
    for signal in output.signal_analyses:
        for check in signal.actionable_checks:
            check["signal_id"] = signal.signal_id
            check["signal_type"] = signal.signal_type
            all_checks.append(check)

    # Sort by priority
    priority_order = {"HIGH": 0, "MED": 1, "LOW": 2}
    all_checks.sort(key=lambda x: priority_order.get(x.get("priority", "MED"), 1))

    return all_checks


def generate_early_warning_dashboard(output: QualityGateOutput) -> dict:
    """
    Extract early warning indicators from expert analysis output.

    Returns dict with quantitative and qualitative indicators.
    """
    if not output or not output.signal_analyses:
        return {"quantitative": [], "qualitative": []}

    quant_indicators = []
    qual_triggers = []

    for signal in output.signal_analyses:
        indicators = signal.early_indicators
        if indicators.get("quantitative_indicators"):
            for ind in indicators["quantitative_indicators"]:
                ind["signal_id"] = signal.signal_id
                quant_indicators.append(ind)
        if indicators.get("qualitative_triggers"):
            for trig in indicators["qualitative_triggers"]:
                trig["signal_id"] = signal.signal_id
                qual_triggers.append(trig)

    return {
        "quantitative": quant_indicators,
        "qualitative": qual_triggers
    }


def get_quality_report(output: QualityGateOutput) -> dict:
    """
    Generate quality report from analysis output.

    Returns dict with quality metrics and validation results.
    """
    if not output:
        return {"status": "NO_OUTPUT", "score": 0}

    return {
        "status": output.output_status,
        "score": output.quality_metrics["overall_quality_score"],
        "null_free_compliance": output.quality_metrics["null_free_compliance"],
        "null_violations": output.quality_metrics["null_violations"],
        "evidence_coverage": output.quality_metrics["evidence_coverage"],
        "counter_evidence_included": output.quality_metrics["counter_evidence_included"],
        "peer_comparison_count": output.quality_metrics["peer_comparison_count"],
        "regulatory_risk_checked": output.quality_metrics["regulatory_risk_checked"],
        "actionable_checks_count": output.quality_metrics["actionable_checks_count"],
        "validation_errors": output.validation_errors,
        "validation_warnings": output.validation_warnings
    }
