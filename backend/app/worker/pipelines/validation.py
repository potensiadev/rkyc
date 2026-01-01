"""
Validation Pipeline Stage
Stage 6: Apply guardrails and validate signals
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# Forbidden expressions and their replacements (PRD Guardrails)
FORBIDDEN_EXPRESSIONS = {
    # Definitive statements -> Probabilistic
    "일 것이다": "로 추정됨",
    "일것이다": "로 추정됨",
    "것이다": "것으로 보임",
    "반드시": "가능성이 높음",
    "확실히": "높은 확률로",
    "분명히": "상당한 가능성으로",
    "틀림없이": "높은 개연성으로",

    # Urgent action -> Review recommendation
    "즉시 조치 필요": "검토 권고",
    "긴급 조치 필요": "조속한 검토 권고",
    "당장": "가급적 빠른 시일 내",
    "지금 바로": "적절한 시점에",

    # Absolute certainty -> Possibility
    "100%": "높은 확률로",
    "절대로": "상당 부분",
    "무조건": "대체로",
}

# Compiled regex patterns for efficiency
FORBIDDEN_PATTERNS = {
    re.compile(re.escape(k)): v
    for k, v in FORBIDDEN_EXPRESSIONS.items()
}


class ValidationPipeline:
    """
    Stage 6: VALIDATION - Apply guardrails to signals

    Validates and sanitizes signals according to PRD guardrails:
    - Replace forbidden expressions with allowed alternatives
    - Validate required fields and evidence
    - Validate enum values
    - Filter invalid signals
    """

    def execute(self, raw_signals: list[dict]) -> list[dict]:
        """
        Execute validation stage.

        Args:
            raw_signals: List of raw signal dicts from SignalExtractionPipeline

        Returns:
            List of validated and sanitized signal dicts
        """
        logger.info(f"VALIDATION stage starting for {len(raw_signals)} signals")

        validated_signals = []

        for i, signal in enumerate(raw_signals):
            try:
                validated = self._validate_signal(signal, i)
                if validated:
                    validated_signals.append(validated)
            except Exception as e:
                logger.warning(f"Signal {i} validation failed: {e}")
                # Continue with other signals

        logger.info(
            f"VALIDATION stage completed: "
            f"{len(validated_signals)}/{len(raw_signals)} signals passed"
        )

        return validated_signals

    def _validate_signal(self, signal: dict, index: int) -> Optional[dict]:
        """
        Validate a single signal.

        Returns validated signal or None if invalid.
        """
        # 1. Validate required fields
        required_fields = [
            "signal_type", "event_type", "impact_direction",
            "impact_strength", "confidence", "title", "summary",
            "corp_id", "event_signature"
        ]

        for field in required_fields:
            if not signal.get(field):
                logger.warning(f"Signal {index} missing required field: {field}")
                return None

        # 2. Validate evidence (at least 1 required per PRD)
        evidence = signal.get("evidence", [])
        if not evidence:
            logger.warning(f"Signal {index} has no evidence (required)")
            return None

        # 3. Validate enums
        if not self._validate_enums(signal, index):
            return None

        # 4. Sanitize text fields (apply guardrails)
        signal = self._sanitize_text_fields(signal)

        # 5. Validate evidence entries
        validated_evidence = []
        for ev in evidence:
            if self._validate_evidence(ev):
                validated_evidence.append(ev)

        if not validated_evidence:
            logger.warning(f"Signal {index} has no valid evidence after validation")
            return None

        signal["evidence"] = validated_evidence

        return signal

    def _validate_enums(self, signal: dict, index: int) -> bool:
        """Validate enum values against allowed values."""
        valid_signal_types = {"DIRECT", "INDUSTRY", "ENVIRONMENT"}
        valid_event_types = {
            "KYC_REFRESH", "INTERNAL_RISK_GRADE_CHANGE", "OVERDUE_FLAG_ON",
            "LOAN_EXPOSURE_CHANGE", "COLLATERAL_CHANGE", "OWNERSHIP_CHANGE",
            "GOVERNANCE_CHANGE", "FINANCIAL_STATEMENT_UPDATE",
            "INDUSTRY_SHOCK", "POLICY_REGULATION_CHANGE"
        }
        valid_directions = {"RISK", "OPPORTUNITY", "NEUTRAL"}
        valid_strengths = {"HIGH", "MED", "LOW"}

        if signal["signal_type"] not in valid_signal_types:
            logger.warning(f"Signal {index} invalid signal_type: {signal['signal_type']}")
            return False

        if signal["event_type"] not in valid_event_types:
            logger.warning(f"Signal {index} invalid event_type: {signal['event_type']}")
            return False

        if signal["impact_direction"] not in valid_directions:
            logger.warning(f"Signal {index} invalid impact_direction: {signal['impact_direction']}")
            return False

        if signal["impact_strength"] not in valid_strengths:
            logger.warning(f"Signal {index} invalid impact_strength: {signal['impact_strength']}")
            return False

        if signal["confidence"] not in valid_strengths:
            logger.warning(f"Signal {index} invalid confidence: {signal['confidence']}")
            return False

        return True

    def _sanitize_text_fields(self, signal: dict) -> dict:
        """Apply guardrail text replacements to signal text fields."""
        text_fields = ["title", "summary"]

        for field in text_fields:
            if field in signal and signal[field]:
                original = signal[field]
                sanitized = self._apply_guardrails(original)
                if original != sanitized:
                    logger.debug(f"Sanitized {field}: '{original[:50]}...' -> '{sanitized[:50]}...'")
                signal[field] = sanitized

        return signal

    def _apply_guardrails(self, text: str) -> str:
        """Replace forbidden expressions with allowed alternatives."""
        result = text
        for pattern, replacement in FORBIDDEN_PATTERNS.items():
            result = pattern.sub(replacement, result)
        return result

    def _validate_evidence(self, evidence: dict) -> bool:
        """Validate a single evidence entry."""
        # evidence_type validation
        valid_evidence_types = {"INTERNAL_FIELD", "DOC", "EXTERNAL"}
        evidence_type = evidence.get("evidence_type", "EXTERNAL")
        if evidence_type not in valid_evidence_types:
            logger.warning(f"Invalid evidence_type: {evidence_type}")
            return False

        # ref_type validation
        valid_ref_types = {"SNAPSHOT_KEYPATH", "DOC_PAGE", "URL"}
        ref_type = evidence.get("ref_type", "URL")
        if ref_type not in valid_ref_types:
            logger.warning(f"Invalid ref_type: {ref_type}")
            return False

        # ref_value is required
        if not evidence.get("ref_value"):
            logger.warning("Evidence missing ref_value")
            return False

        return True
