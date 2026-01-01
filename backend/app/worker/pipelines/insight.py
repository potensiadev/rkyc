"""
Insight Pipeline Stage
Stage 8: Generate final briefing using LLM
"""

import logging
from typing import Optional

from app.worker.llm.service import LLMService
from app.worker.llm.prompts import INSIGHT_GENERATION_PROMPT
from app.worker.llm.exceptions import AllProvidersFailedError

logger = logging.getLogger(__name__)


class InsightPipeline:
    """
    Stage 8: INSIGHT - Generate final briefing summary

    Uses LLM to generate a concise executive briefing
    summarizing all detected signals and their implications.
    """

    def __init__(self):
        self.llm = LLMService()

    def execute(self, signals: list[dict], context: dict) -> str:
        """
        Execute insight generation stage.

        Args:
            signals: List of validated signal dicts
            context: Unified context from ContextPipeline

        Returns:
            Generated insight/briefing string
        """
        corp_id = context.get("corp_id", "")
        corp_name = context.get("corp_name", "")

        logger.info(f"INSIGHT stage starting for corp_id={corp_id}")

        # Handle no signals case
        if not signals:
            insight = self._generate_no_signals_insight(corp_name)
            logger.info("INSIGHT stage completed (no signals)")
            return insight

        try:
            insight = self._generate_insight(signals, context)
            logger.info(f"INSIGHT stage completed: {len(insight)} chars")
            return insight

        except AllProvidersFailedError as e:
            logger.error(f"LLM failed for insight generation: {e}")
            return self._generate_fallback_insight(signals, corp_name)

        except Exception as e:
            logger.error(f"Insight generation failed: {e}")
            return self._generate_fallback_insight(signals, corp_name)

    def _generate_insight(self, signals: list[dict], context: dict) -> str:
        """Generate insight using LLM."""
        # Build signal summary for prompt
        signal_summary = self._build_signal_summary(signals)

        user_prompt = INSIGHT_GENERATION_PROMPT.format(
            corp_name=context.get("corp_name", ""),
            industry_code=context.get("industry_code", ""),
            industry_name=context.get("industry_name", ""),
            signal_count=len(signals),
            signals_summary=signal_summary,
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a senior risk analyst providing executive briefings. "
                    "Generate concise, actionable insights in Korean. "
                    "Use probabilistic language: '~로 추정됨', '~가능성 있음', '검토 권고'. "
                    "Avoid definitive statements like '반드시', '즉시 조치 필요'."
                ),
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ]

        # Use call_with_fallback for text response
        insight = self.llm.call_with_fallback(
            messages=messages,
            temperature=0.3,
            max_tokens=1000,
        )

        return insight.strip()

    def _build_signal_summary(self, signals: list[dict]) -> str:
        """Build signal summary for LLM prompt."""
        lines = []

        # Group by impact direction
        risk_signals = [s for s in signals if s.get("impact_direction") == "RISK"]
        opp_signals = [s for s in signals if s.get("impact_direction") == "OPPORTUNITY"]
        neutral_signals = [s for s in signals if s.get("impact_direction") == "NEUTRAL"]

        if risk_signals:
            lines.append(f"## 리스크 시그널 ({len(risk_signals)}건)")
            for s in risk_signals:
                strength = s.get("impact_strength", "MED")
                lines.append(f"- [{strength}] {s.get('title', '')}: {s.get('summary', '')[:100]}")

        if opp_signals:
            lines.append(f"\n## 기회 시그널 ({len(opp_signals)}건)")
            for s in opp_signals:
                strength = s.get("impact_strength", "MED")
                lines.append(f"- [{strength}] {s.get('title', '')}: {s.get('summary', '')[:100]}")

        if neutral_signals:
            lines.append(f"\n## 참고 시그널 ({len(neutral_signals)}건)")
            for s in neutral_signals:
                lines.append(f"- {s.get('title', '')}: {s.get('summary', '')[:100]}")

        return "\n".join(lines)

    def _generate_no_signals_insight(self, corp_name: str) -> str:
        """Generate insight when no signals detected."""
        return (
            f"{corp_name}에 대한 분석 결과, 새로운 리스크 시그널이 발견되지 않았습니다. "
            "현재 기준으로 특별한 위험 요인은 관찰되지 않으나, "
            "지속적인 모니터링이 권고됩니다."
        )

    def _generate_fallback_insight(self, signals: list[dict], corp_name: str) -> str:
        """Generate basic insight without LLM (fallback)."""
        risk_count = sum(1 for s in signals if s.get("impact_direction") == "RISK")
        opp_count = sum(1 for s in signals if s.get("impact_direction") == "OPPORTUNITY")
        high_count = sum(1 for s in signals if s.get("impact_strength") == "HIGH")

        insight_parts = [f"{corp_name}에 대해 {len(signals)}개의 시그널이 감지되었습니다."]

        if risk_count > 0:
            insight_parts.append(f"리스크 시그널 {risk_count}건")
        if opp_count > 0:
            insight_parts.append(f"기회 시그널 {opp_count}건")
        if high_count > 0:
            insight_parts.append(f"(HIGH 강도 {high_count}건 포함)")

        insight_parts.append("상세 내용은 시그널 목록을 참조하시기 바랍니다.")

        return " ".join(insight_parts)
