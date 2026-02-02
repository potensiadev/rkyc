"""
Base Signal Agent - Abstract base class for all signal agents

Sprint 2: Signal Multi-Agent Architecture (ADR-009)

Features:
- Shared validation logic
- Common signature computation
- Agent-specific LLM tracking
- Forbidden word detection
"""

import hashlib
import logging
import re
import time
from abc import ABC, abstractmethod
from typing import Optional

from app.worker.llm.service import LLMService
from app.worker.llm.usage_tracker import log_llm_usage
from app.worker.llm.exceptions import AllProvidersFailedError

logger = logging.getLogger(__name__)


# =============================================================================
# Shared Validation Constants
# =============================================================================

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
    "것으로 보인다",
]

FORBIDDEN_PATTERNS = [re.compile(re.escape(word)) for word in FORBIDDEN_WORDS]

MAX_TITLE_LENGTH = 50
MAX_SUMMARY_LENGTH = 200


class BaseSignalAgent(ABC):
    """
    Abstract base class for all signal extraction agents.

    Each agent specializes in one signal_type:
    - DirectSignalAgent: DIRECT (8 event_types)
    - IndustrySignalAgent: INDUSTRY (1 event_type)
    - EnvironmentSignalAgent: ENVIRONMENT (1 event_type)

    Shared features:
    - LLM service with usage tracking
    - Validation and enrichment logic
    - Signature computation for deduplication
    """

    # Subclasses must define these
    AGENT_NAME: str = "base"
    SIGNAL_TYPE: str = ""
    ALLOWED_EVENT_TYPES: set[str] = set()

    def __init__(self):
        self.llm = LLMService()
        self._trace_id: Optional[str] = None

    @abstractmethod
    def get_system_prompt(self, corp_name: str, industry_name: str) -> str:
        """Return agent-specific system prompt."""
        pass

    @abstractmethod
    def get_user_prompt(self, context: dict) -> str:
        """Return agent-specific user prompt."""
        pass

    @abstractmethod
    def get_relevant_events(self, context: dict) -> list[dict]:
        """Extract relevant events for this agent from context."""
        pass

    def execute(self, context: dict) -> list[dict]:
        """
        Execute signal extraction for this agent's signal_type.

        Args:
            context: Unified context from ContextPipeline

        Returns:
            List of validated signal dicts
        """
        corp_id = context.get("corp_id", "")
        corp_name = context.get("corp_name", "")
        industry_name = context.get("industry_name", "")

        # Set trace ID for this execution
        self._trace_id = f"{self.AGENT_NAME}_{corp_id}_{int(time.time() * 1000)}"

        logger.info(
            f"[{self.AGENT_NAME}] Starting signal extraction for "
            f"corp_id={corp_id}, signal_type={self.SIGNAL_TYPE}"
        )

        # Get relevant events for this agent
        relevant_events = self.get_relevant_events(context)
        if not relevant_events and self.SIGNAL_TYPE != "DIRECT":
            # DIRECT can still extract signals from internal snapshot
            logger.info(
                f"[{self.AGENT_NAME}] No relevant events, skipping "
                f"(signal_type={self.SIGNAL_TYPE})"
            )
            return []

        # Build prompts
        system_prompt = self.get_system_prompt(corp_name, industry_name)
        user_prompt = self.get_user_prompt(context)

        start_time = time.time()

        try:
            # Call LLM with agent-specific tracking
            # P0-5 Fix: Pass trace_id for observability
            # Use sync version since execute() is not async
            signals = self.llm.extract_signals_sync(
                context=context,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                agent_name=self.AGENT_NAME,
                trace_id=self._trace_id,
            )

            latency_ms = int((time.time() - start_time) * 1000)

            # Validate and enrich signals
            validated_signals = []
            for signal in signals:
                # Force signal_type to this agent's type
                signal["signal_type"] = self.SIGNAL_TYPE

                enriched = self._enrich_signal(signal, context)
                if enriched:
                    validated_signals.append(enriched)

            logger.info(
                f"[{self.AGENT_NAME}] Completed: {len(validated_signals)}/{len(signals)} "
                f"signals validated (latency={latency_ms}ms)"
            )

            return validated_signals

        except AllProvidersFailedError as e:
            logger.error(
                f"[{self.AGENT_NAME}] All LLM providers failed for "
                f"corp_id={corp_id}: {e}"
            )
            return []
        except Exception as e:
            logger.error(
                f"[{self.AGENT_NAME}] Signal extraction failed for "
                f"corp_id={corp_id}: {e}"
            )
            raise

    def _enrich_signal(self, signal: dict, context: dict) -> Optional[dict]:
        """
        Validate and enrich signal with metadata.

        Validation rules:
        1. Required fields present
        2. Evidence exists (minimum 1)
        3. Valid enum values
        4. Event type in allowed set
        5. Forbidden words check
        6. Length constraints

        Returns None if signal is invalid.
        """
        # 1. Required fields
        required_fields = [
            "signal_type", "event_type", "impact_direction",
            "impact_strength", "confidence", "title", "summary"
        ]
        for field in required_fields:
            if not signal.get(field):
                logger.warning(
                    f"[{self.AGENT_NAME}] Signal missing field: {field}"
                )
                return None

        # 2. Evidence check
        evidence = signal.get("evidence", [])
        if not evidence:
            logger.warning(f"[{self.AGENT_NAME}] Signal has no evidence")
            return None

        # 3. Enum validation
        valid_directions = {"RISK", "OPPORTUNITY", "NEUTRAL"}
        valid_strengths = {"HIGH", "MED", "LOW"}

        if signal["impact_direction"] not in valid_directions:
            logger.warning(
                f"[{self.AGENT_NAME}] Invalid impact_direction: "
                f"{signal['impact_direction']}"
            )
            return None

        if signal["impact_strength"] not in valid_strengths:
            logger.warning(
                f"[{self.AGENT_NAME}] Invalid impact_strength: "
                f"{signal['impact_strength']}"
            )
            return None

        if signal["confidence"] not in valid_strengths:
            logger.warning(
                f"[{self.AGENT_NAME}] Invalid confidence: {signal['confidence']}"
            )
            return None

        # 4. Event type validation
        event_type = signal.get("event_type", "")
        if event_type not in self.ALLOWED_EVENT_TYPES:
            logger.warning(
                f"[{self.AGENT_NAME}] Invalid event_type '{event_type}' "
                f"for signal_type '{self.SIGNAL_TYPE}'. "
                f"Allowed: {self.ALLOWED_EVENT_TYPES}"
            )
            return None

        # 5. Forbidden words check
        summary = signal.get("summary", "")
        title = signal.get("title", "")

        for pattern in FORBIDDEN_PATTERNS:
            if pattern.search(summary):
                logger.warning(
                    f"[{self.AGENT_NAME}] Forbidden word in summary: "
                    f"'{pattern.pattern}'"
                )
                return None
            if pattern.search(title):
                logger.warning(
                    f"[{self.AGENT_NAME}] Forbidden word in title: "
                    f"'{pattern.pattern}'"
                )
                return None

        # 6. Length constraints (truncate if needed)
        if len(title) > MAX_TITLE_LENGTH:
            logger.warning(
                f"[{self.AGENT_NAME}] Title too long, truncating"
            )
            signal["title"] = title[:MAX_TITLE_LENGTH]

        if len(summary) > MAX_SUMMARY_LENGTH:
            logger.warning(
                f"[{self.AGENT_NAME}] Summary too long, truncating"
            )
            signal["summary"] = summary[:MAX_SUMMARY_LENGTH]

        # Add metadata
        signal["corp_id"] = context.get("corp_id", "")
        signal["snapshot_version"] = context.get("snapshot_version", 0)
        signal["event_signature"] = self._compute_signature(signal)
        signal["extracted_by"] = self.AGENT_NAME

        return signal

    def _compute_signature(self, signal: dict) -> str:
        """
        Compute event_signature for deduplication.

        Signature based on:
        - signal_type
        - event_type
        - evidence ref_values (sorted)
        """
        evidence_refs = sorted([
            ev.get("ref_value", "")
            for ev in signal.get("evidence", [])
        ])

        sig_string = "|".join([
            signal.get("signal_type", ""),
            signal.get("event_type", ""),
            ",".join(evidence_refs),
        ])

        return hashlib.sha256(sig_string.encode()).hexdigest()
