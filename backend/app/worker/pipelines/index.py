"""
Index Pipeline Stage
Stage 7: Save validated signals to database
"""

import logging
from datetime import datetime
from uuid import uuid4
from typing import Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.worker.db import get_sync_db
from app.models.signal import Signal, Evidence, SignalIndex

logger = logging.getLogger(__name__)


class DuplicateSignalError(Exception):
    """Raised when signal already exists (same event_signature)"""
    pass


class IndexPipeline:
    """
    Stage 7: INDEX - Save signals to database

    Creates records in:
    - rkyc_signal: Main signal data
    - rkyc_evidence: Evidence for each signal
    - rkyc_signal_index: Denormalized index for dashboard
    """

    def execute(self, validated_signals: list[dict], context: dict) -> list[str]:
        """
        Execute index stage.

        Args:
            validated_signals: List of validated signal dicts
            context: Unified context for corporation info

        Returns:
            List of created signal IDs
        """
        corp_id = context.get("corp_id", "")
        logger.info(
            f"INDEX stage starting for corp_id={corp_id}, "
            f"signals={len(validated_signals)}"
        )

        if not validated_signals:
            logger.info("No signals to index")
            return []

        created_signal_ids = []

        with get_sync_db() as db:
            for signal_data in validated_signals:
                try:
                    signal_id = self._create_signal(db, signal_data, context)
                    if signal_id:
                        created_signal_ids.append(signal_id)
                except DuplicateSignalError as e:
                    logger.warning(f"Skipping duplicate signal: {e}")
                except Exception as e:
                    logger.error(f"Failed to create signal: {e}")
                    # Continue with other signals

            db.commit()

        logger.info(f"INDEX stage completed: created {len(created_signal_ids)} signals")
        return created_signal_ids

    def _create_signal(self, db, signal_data: dict, context: dict) -> Optional[str]:
        """
        Create a single signal with evidence and index entry.

        Returns signal_id if created, None if skipped.
        """
        corp_id = signal_data.get("corp_id", "")
        event_signature = signal_data.get("event_signature", "")

        # Check for duplicate
        existing = db.execute(
            select(Signal).where(
                Signal.corp_id == corp_id,
                Signal.event_signature == event_signature,
            )
        ).scalar_one_or_none()

        if existing:
            raise DuplicateSignalError(f"Signal with signature {event_signature[:16]}... already exists")

        # Create Signal
        signal_id = uuid4()
        signal = Signal(
            signal_id=signal_id,
            corp_id=corp_id,
            signal_type=signal_data["signal_type"],
            event_type=signal_data["event_type"],
            event_signature=event_signature,
            snapshot_version=signal_data.get("snapshot_version", 0),
            impact_direction=signal_data["impact_direction"],
            impact_strength=signal_data["impact_strength"],
            confidence=signal_data["confidence"],
            summary=signal_data["summary"],
        )
        db.add(signal)
        db.flush()  # Get signal_id

        # Create Evidence entries
        evidence_count = 0
        for ev_data in signal_data.get("evidence", []):
            evidence = Evidence(
                evidence_id=uuid4(),
                signal_id=signal_id,
                evidence_type=ev_data.get("evidence_type", "EXTERNAL"),
                ref_type=ev_data.get("ref_type", "URL"),
                ref_value=ev_data.get("ref_value", ""),
                snippet=ev_data.get("snippet", "")[:400] if ev_data.get("snippet") else None,
                meta=ev_data.get("meta"),
            )
            db.add(evidence)
            evidence_count += 1

        # Create SignalIndex (denormalized for dashboard)
        index = SignalIndex(
            index_id=uuid4(),
            corp_id=corp_id,
            corp_name=context.get("corp_name", ""),
            industry_code=context.get("industry_code", ""),
            signal_type=signal_data["signal_type"],
            event_type=signal_data["event_type"],
            impact_direction=signal_data["impact_direction"],
            impact_strength=signal_data["impact_strength"],
            confidence=signal_data["confidence"],
            title=signal_data.get("title", signal_data["summary"][:50]),
            summary_short=signal_data["summary"][:200],
            evidence_count=evidence_count,
            detected_at=datetime.utcnow(),
            signal_id=signal_id,
        )
        db.add(index)

        logger.debug(f"Created signal {signal_id} with {evidence_count} evidence items")
        return str(signal_id)
