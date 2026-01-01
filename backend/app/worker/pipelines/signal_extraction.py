"""
Signal Extraction Pipeline Stage
Stage 5: Extract risk signals using LLM
"""

import json
import hashlib
import logging
from typing import Optional

from app.worker.llm.service import LLMService
from app.worker.llm.prompts import (
    SIGNAL_EXTRACTION_SYSTEM,
    format_signal_extraction_prompt,
)
from app.worker.llm.exceptions import AllProvidersFailedError

logger = logging.getLogger(__name__)


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

        # Format prompt with context data
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
        Enrich signal with metadata and compute event signature.

        Returns None if signal is invalid.
        """
        # Validate required fields
        required_fields = [
            "signal_type", "event_type", "impact_direction",
            "impact_strength", "confidence", "title", "summary"
        ]
        for field in required_fields:
            if not signal.get(field):
                logger.warning(f"Signal missing required field: {field}")
                return None

        # Validate evidence
        evidence = signal.get("evidence", [])
        if not evidence:
            logger.warning("Signal has no evidence, skipping")
            return None

        # Validate enums
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
            logger.warning(f"Invalid signal_type: {signal['signal_type']}")
            return None
        if signal["event_type"] not in valid_event_types:
            logger.warning(f"Invalid event_type: {signal['event_type']}")
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

        # Add metadata
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
