"""
Insight Pipeline Stage
Stage 8: Generate final briefing using LLM with similar case search
"""

import logging
from typing import Optional

from sqlalchemy import text

from app.worker.db import get_sync_db
from app.worker.llm.service import LLMService
from app.worker.llm.prompts import INSIGHT_GENERATION_PROMPT
from app.worker.llm.exceptions import AllProvidersFailedError
from app.worker.llm.embedding import get_embedding_service, EmbeddingError

logger = logging.getLogger(__name__)


class InsightPipeline:
    """
    Stage 8: INSIGHT - Generate final briefing summary with similar case search

    Uses LLM to generate a concise executive briefing
    summarizing all detected signals and their implications.

    Enhanced with:
    - Similar case search using embedding vectors
    - Past case context for better insights
    """

    def __init__(self):
        self.llm = LLMService()
        self.embedding_service = get_embedding_service()

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

        # Find similar past cases for context
        similar_cases = []
        if self.embedding_service.is_available:
            try:
                similar_cases = self._find_similar_cases(signals)
                logger.info(f"Found {len(similar_cases)} similar past cases")
            except Exception as e:
                logger.warning(f"Similar case search failed (non-fatal): {e}")

        try:
            insight = self._generate_insight(signals, context, similar_cases)
            logger.info(f"INSIGHT stage completed: {len(insight)} chars")
            return insight

        except AllProvidersFailedError as e:
            logger.error(f"LLM failed for insight generation: {e}")
            return self._generate_fallback_insight(signals, corp_name)

        except Exception as e:
            logger.error(f"Insight generation failed: {e}")
            return self._generate_fallback_insight(signals, corp_name)

    def _generate_insight(
        self,
        signals: list[dict],
        context: dict,
        similar_cases: list[dict] = None,
    ) -> str:
        """Generate insight using LLM with similar case context."""
        # Build signal summary for prompt
        signal_summary = self._build_signal_summary(signals)

        # Build similar cases summary
        similar_cases_summary = ""
        if similar_cases:
            similar_cases_summary = self._build_similar_cases_summary(similar_cases)

        user_prompt = INSIGHT_GENERATION_PROMPT.format(
            corp_name=context.get("corp_name", ""),
            industry_code=context.get("industry_code", ""),
            industry_name=context.get("industry_name", ""),
            signal_count=len(signals),
            signals_summary=signal_summary,
        )

        # Add similar cases to prompt if available
        if similar_cases_summary:
            user_prompt += f"\n\n### 유사 과거 케이스 참고\n{similar_cases_summary}"

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a senior risk analyst providing executive briefings. "
                    "Generate concise, actionable insights in Korean. "
                    "Use probabilistic language: '~로 추정됨', '~가능성 있음', '검토 권고'. "
                    "Avoid definitive statements like '반드시', '즉시 조치 필요'. "
                    "If similar past cases are provided, reference them to provide historical context."
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

    def _find_similar_cases(
        self,
        signals: list[dict],
        limit: int = 5,
        similarity_threshold: float = 0.7,
    ) -> list[dict]:
        """
        Find similar past cases using embedding similarity.

        Args:
            signals: Current signals to find similar cases for
            limit: Maximum number of similar cases to return
            similarity_threshold: Minimum similarity score (0-1)

        Returns:
            List of similar case dicts with similarity scores
        """
        if not signals:
            return []

        # Use the most significant signal for case search
        # (typically HIGH impact or first signal)
        high_impact = [s for s in signals if s.get("impact_strength") == "HIGH"]
        target_signal = high_impact[0] if high_impact else signals[0]

        # Generate embedding for target signal
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

            # Query similar cases from database
            embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

            with get_sync_db() as db:
                # Use the helper function from migration
                result = db.execute(
                    text("""
                        SELECT
                            case_id,
                            corp_id,
                            industry_code,
                            signal_type,
                            event_type,
                            summary,
                            1 - (embedding <=> :embedding::vector) AS similarity
                        FROM rkyc_case_index
                        WHERE embedding IS NOT NULL
                          AND 1 - (embedding <=> :embedding::vector) >= :threshold
                        ORDER BY embedding <=> :embedding::vector
                        LIMIT :limit
                    """),
                    {
                        "embedding": embedding_str,
                        "threshold": similarity_threshold,
                        "limit": limit,
                    }
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
                        "similarity": round(row.similarity, 3),
                    })

                return cases

        except EmbeddingError as e:
            logger.warning(f"Embedding generation failed for case search: {e}")
            return []
        except Exception as e:
            logger.warning(f"Similar case search query failed: {e}")
            return []

    def _build_similar_cases_summary(self, cases: list[dict]) -> str:
        """Build summary text for similar cases."""
        if not cases:
            return ""

        lines = []
        for i, case in enumerate(cases, 1):
            similarity_pct = int(case.get("similarity", 0) * 100)
            lines.append(
                f"{i}. [{case.get('signal_type', 'N/A')}] {case.get('event_type', 'N/A')} "
                f"(유사도 {similarity_pct}%)\n"
                f"   - 업종: {case.get('industry_code', 'N/A')}\n"
                f"   - 요약: {case.get('summary', 'N/A')[:100]}..."
            )

        return "\n".join(lines)

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
