"""
Deduplication Pipeline
Detect and filter duplicate signals based on event_signature
"""

import logging
from typing import Optional

from sqlalchemy import select

from app.worker.db import get_sync_db
from app.models.signal import Signal

logger = logging.getLogger(__name__)


class DeduplicationPipeline:
    """
    Deduplication filter for signals.

    Filters out signals that already exist in the database
    based on their event_signature (SHA256 hash).
    """

    def execute(self, signals: list[dict], corp_id: str) -> list[dict]:
        """
        Execute deduplication.

        Args:
            signals: List of validated signal dicts
            corp_id: Corporation ID to scope the search

        Returns:
            List of signals that are not duplicates
        """
        if not signals:
            return []

        logger.info(f"DEDUPLICATION starting for {len(signals)} signals")

        # Extract signatures from input signals
        input_signatures = {
            s.get("event_signature"): s
            for s in signals
            if s.get("event_signature")
        }

        if not input_signatures:
            logger.warning("No valid event_signatures in signals")
            return []

        # Query existing signatures from database
        existing_signatures = self._get_existing_signatures(
            corp_id, list(input_signatures.keys())
        )

        # Filter out duplicates
        unique_signals = []
        duplicate_count = 0

        for signature, signal in input_signatures.items():
            if signature in existing_signatures:
                logger.debug(f"Duplicate signal detected: {signature[:16]}...")
                duplicate_count += 1
            else:
                unique_signals.append(signal)

        logger.info(
            f"DEDUPLICATION completed: "
            f"{len(unique_signals)} unique, {duplicate_count} duplicates filtered"
        )

        return unique_signals

    def _get_existing_signatures(
        self, corp_id: str, signatures: list[str]
    ) -> set[str]:
        """
        Query database for existing signal signatures.

        Args:
            corp_id: Corporation ID
            signatures: List of signatures to check

        Returns:
            Set of signatures that already exist
        """
        if not signatures:
            return set()

        with get_sync_db() as db:
            # Query for existing signals with matching signatures
            stmt = select(Signal.event_signature).where(
                Signal.corp_id == corp_id,
                Signal.event_signature.in_(signatures),
            )
            result = db.execute(stmt).fetchall()
            existing = {row[0] for row in result}

        logger.debug(f"Found {len(existing)} existing signatures in database")
        return existing


def deduplicate_within_batch(signals: list[dict]) -> list[dict]:
    """
    Remove duplicates within a single batch of signals.

    This handles cases where the LLM generates duplicate signals
    in the same extraction run.

    Args:
        signals: List of signal dicts

    Returns:
        List of unique signals (first occurrence kept)
    """
    seen_signatures = set()
    unique_signals = []

    for signal in signals:
        signature = signal.get("event_signature")
        if not signature:
            # Keep signals without signatures (should be rare)
            unique_signals.append(signal)
            continue

        if signature not in seen_signatures:
            seen_signatures.add(signature)
            unique_signals.append(signal)

    removed = len(signals) - len(unique_signals)
    if removed > 0:
        logger.info(f"Removed {removed} intra-batch duplicates")

    return unique_signals
