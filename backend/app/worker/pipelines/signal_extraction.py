"""
Signal Extraction Pipeline Stage
Stage 5: Extract risk signals using LLM

Production-grade validation with:
- Forbidden word detection
- Headline length validation
- Signal type / Event type mapping validation
- Confidence-based source verification
"""

import json
import hashlib
import logging
import re
from typing import Optional

from app.worker.llm.service import LLMService
from app.worker.llm.prompts import (
    SIGNAL_EXTRACTION_SYSTEM,
    format_signal_extraction_prompt,
)
from app.worker.llm.exceptions import AllProvidersFailedError

logger = logging.getLogger(__name__)

# =============================================================================
# Validation Rules
# =============================================================================

# Forbidden words in summary (auto-fail if present)
FORBIDDEN_WORDS = [
    "반드시",
    "즉시",
    "확실히",
    "틀림없이",
    "무조건",
    "긴급",
    "예상됨",
    "전망됨",
    "~할 것이다",
    "~일 것이다",
    "것으로 보인다",  # Too speculative
]

# Compiled regex patterns for forbidden words
FORBIDDEN_PATTERNS = [re.compile(re.escape(word)) for word in FORBIDDEN_WORDS]

# Signal Type to allowed Event Types mapping
SIGNAL_EVENT_MAPPING = {
    "DIRECT": {
        "KYC_REFRESH",
        "INTERNAL_RISK_GRADE_CHANGE",
        "OVERDUE_FLAG_ON",
        "LOAN_EXPOSURE_CHANGE",
        "COLLATERAL_CHANGE",
        "OWNERSHIP_CHANGE",
        "GOVERNANCE_CHANGE",
        "FINANCIAL_STATEMENT_UPDATE",
    },
    "INDUSTRY": {"INDUSTRY_SHOCK"},
    "ENVIRONMENT": {"POLICY_REGULATION_CHANGE"},
}

# Maximum lengths (PRD 14.7 rkyc_signal schema)
MAX_TITLE_LENGTH = 50
MAX_SUMMARY_LENGTH = 200


class SignalExtractionPipeline:
    """
    Stage 5: SIGNAL - Extract risk signals using LLM

    Uses Claude Sonnet 4 (with GPT-4o fallback) to analyze
    unified context and extract risk signals.
    """

    def __init__(self):
        self.llm = LLMService()

    def execute(self, context: dict) -> list[dict]:
        """
        Execute signal extraction stage.

        Args:
            context: Unified context from ContextPipeline

        Returns:
            list of signal dicts with structure:
                - signal_type: DIRECT|INDUSTRY|ENVIRONMENT
                - event_type: One of 10 event types
                - impact_direction: RISK|OPPORTUNITY|NEUTRAL
                - impact_strength: HIGH|MED|LOW
                - confidence: HIGH|MED|LOW
                - title: Short title
                - summary: Detailed summary
                - evidence: List of evidence dicts
                - corp_id: Corporation ID
                - snapshot_version: Snapshot version
                - event_signature: SHA256 hash for deduplication
        """
        corp_id = context.get("corp_id", "")
        logger.info(f"SIGNAL stage starting for corp_id={corp_id}")

        # Format prompt with context data (3-track events)
        user_prompt = format_signal_extraction_prompt(
            corp_name=context.get("corp_name", ""),
            corp_reg_no=context.get("corp_reg_no", ""),
            industry_code=context.get("industry_code", ""),
            industry_name=context.get("industry_name", ""),
            snapshot_json=json.dumps(
                context.get("snapshot_json", {}),
                ensure_ascii=False,
                indent=2,
            ),
            external_events=json.dumps(
                context.get("external_events", []),
                ensure_ascii=False,
                indent=2,
            ),
            # New 3-track events
            direct_events=json.dumps(
                context.get("direct_events", []),
                ensure_ascii=False,
                indent=2,
            ),
            industry_events=json.dumps(
                context.get("industry_events", []),
                ensure_ascii=False,
                indent=2,
            ),
            environment_events=json.dumps(
                context.get("environment_events", []),
                ensure_ascii=False,
                indent=2,
            ),
        )

        logger.info(
            f"SIGNAL extraction with 3-track events: "
            f"direct={len(context.get('direct_events', []))}, "
            f"industry={len(context.get('industry_events', []))}, "
            f"environment={len(context.get('environment_events', []))}"
        )

        try:
            # Call LLM for signal extraction
            signals = self.llm.extract_signals(
                context=context,
                system_prompt=SIGNAL_EXTRACTION_SYSTEM,
                user_prompt=user_prompt,
            )

            # Enrich signals with metadata
            enriched_signals = []
            for signal in signals:
                enriched = self._enrich_signal(signal, context)
                if enriched:
                    enriched_signals.append(enriched)

            logger.info(
                f"SIGNAL stage completed: extracted {len(enriched_signals)} signals"
            )
            return enriched_signals

        except AllProvidersFailedError as e:
            logger.error(f"All LLM providers failed for corp_id={corp_id}: {e}")
            # Return empty list on LLM failure (pipeline continues with no signals)
            return []

        except Exception as e:
            logger.error(f"Signal extraction failed for corp_id={corp_id}: {e}")
            raise

    def _enrich_signal(self, signal: dict, context: dict) -> Optional[dict]:
        """
        Enrich signal with metadata and validate.

        Validation rules:
        1. Required fields present
        2. Evidence exists (minimum 1)
        3. Valid enum values
        4. Signal type / Event type mapping
        5. Forbidden words check
        6. Length constraints (headline, title, summary)

        Returns None if signal is invalid.
        """
        # 1. Validate required fields
        required_fields = [
            "signal_type", "event_type", "impact_direction",
            "impact_strength", "confidence", "title", "summary"
        ]
        for field in required_fields:
            if not signal.get(field):
                logger.warning(f"Signal missing required field: {field}")
                return None

        # 2. Validate evidence
        evidence = signal.get("evidence", [])
        if not evidence:
            logger.warning("Signal has no evidence, skipping")
            return None

        # 3. Validate enums
        valid_directions = {"RISK", "OPPORTUNITY", "NEUTRAL"}
        valid_strengths = {"HIGH", "MED", "LOW"}

        signal_type = signal["signal_type"]
        event_type = signal["event_type"]

        if signal_type not in SIGNAL_EVENT_MAPPING:
            logger.warning(f"Invalid signal_type: {signal_type}")
            return None

        if signal["impact_direction"] not in valid_directions:
            logger.warning(f"Invalid impact_direction: {signal['impact_direction']}")
            return None
        if signal["impact_strength"] not in valid_strengths:
            logger.warning(f"Invalid impact_strength: {signal['impact_strength']}")
            return None
        if signal["confidence"] not in valid_strengths:
            logger.warning(f"Invalid confidence: {signal['confidence']}")
            return None

        # 4. Validate signal_type / event_type mapping
        allowed_events = SIGNAL_EVENT_MAPPING[signal_type]
        if event_type not in allowed_events:
            logger.warning(
                f"Invalid event_type '{event_type}' for signal_type '{signal_type}'. "
                f"Allowed: {allowed_events}"
            )
            return None

        # 5. Check forbidden words in summary
        summary = signal.get("summary", "")
        for pattern in FORBIDDEN_PATTERNS:
            if pattern.search(summary):
                logger.warning(
                    f"Signal summary contains forbidden word, skipping: "
                    f"'{pattern.pattern}' in '{summary[:50]}...'"
                )
                return None

        # Also check title for forbidden words
        title = signal.get("title", "")
        if title:
            for pattern in FORBIDDEN_PATTERNS:
                if pattern.search(title):
                    logger.warning(
                        f"Signal title contains forbidden word: '{pattern.pattern}'"
                    )
                    return None

        # 6. Validate length constraints
        if len(title) > MAX_TITLE_LENGTH:
            logger.warning(
                f"Title too long ({len(title)} > {MAX_TITLE_LENGTH}), truncating"
            )
            signal["title"] = title[:MAX_TITLE_LENGTH]

        if len(summary) > MAX_SUMMARY_LENGTH:
            logger.warning(
                f"Summary too long ({len(summary)} > {MAX_SUMMARY_LENGTH}), truncating"
            )
            signal["summary"] = summary[:MAX_SUMMARY_LENGTH]

        # Add metadata (PRD 14.7 rkyc_signal schema)
        signal["corp_id"] = context.get("corp_id", "")
        signal["snapshot_version"] = context.get("snapshot_version", 0)
        signal["event_signature"] = self._compute_signature(signal)

        return signal

    def _compute_signature(self, signal: dict) -> str:
        """
        Compute event_signature for deduplication.

        Signature is based on:
        - signal_type
        - event_type
        - evidence ref_values (sorted)
        """
        # Get sorted evidence references
        evidence_refs = sorted([
            ev.get("ref_value", "")
            for ev in signal.get("evidence", [])
        ])

        # Create signature string
        sig_string = "|".join([
            signal.get("signal_type", ""),
            signal.get("event_type", ""),
            ",".join(evidence_refs),
        ])

        # Compute SHA256 hash
        return hashlib.sha256(sig_string.encode()).hexdigest()
