"""
Index Pipeline Stage
Stage 7: Save validated signals to database with embedding vectors
"""

import logging
from datetime import datetime, UTC
from uuid import uuid4
from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert

from app.worker.db import get_sync_db
from app.models.signal import (
    Signal, Evidence, SignalIndex,
    SignalType, EventType, ImpactDirection, ImpactStrength, ConfidenceLevel,
)
from app.worker.llm.embedding import get_embedding_service, EmbeddingError

logger = logging.getLogger(__name__)


def _safe_enum_convert(enum_class, value, default=None):
    """Safely convert string to Enum, returning default if conversion fails"""
    if value is None:
        return default
    if isinstance(value, enum_class):
        return value
    try:
        return enum_class(value)
    except (ValueError, KeyError):
        logger.warning(f"Invalid enum value '{value}' for {enum_class.__name__}, using default: {default}")
        return default


class DuplicateSignalError(Exception):
    """Raised when signal already exists (same event_signature)"""
    pass


class IndexPipeline:
    """
    Stage 7: INDEX - Save signals to database with embeddings

    Creates records in:
    - rkyc_signal: Main signal data
    - rkyc_evidence: Evidence for each signal
    - rkyc_signal_index: Denormalized index for dashboard
    - rkyc_signal_embedding: Embedding vectors for semantic search
    """

    def __init__(self):
        self.embedding_service = get_embedding_service()

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
        signals_for_embedding = []

        with get_sync_db() as db:
            for signal_data in validated_signals:
                try:
                    signal_id = self._create_signal(db, signal_data, context)
                    if signal_id:
                        created_signal_ids.append(signal_id)
                        # Collect for batch embedding
                        signals_for_embedding.append({
                            "signal_id": signal_id,
                            "title": signal_data.get("title", ""),
                            "summary": signal_data.get("summary", ""),
                            "signal_type": signal_data.get("signal_type", ""),
                            "event_type": signal_data.get("event_type", ""),
                        })
                except DuplicateSignalError as e:
                    logger.warning(f"Skipping duplicate signal: {e}")
                except Exception as e:
                    logger.error(f"Failed to create signal: {e}")
                    # Continue with other signals

            db.commit()

            # Generate and store embeddings (non-blocking)
            if signals_for_embedding and self.embedding_service.is_available:
                self._store_embeddings(db, signals_for_embedding)
                db.commit()

        logger.info(f"INDEX stage completed: created {len(created_signal_ids)} signals")
        return created_signal_ids

    def _check_embedding_table_exists(self, db) -> bool:
        """Check if rkyc_signal_embedding table exists (pgvector installed)"""
        try:
            result = db.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'rkyc_signal_embedding'
                )
            """))
            return result.scalar() or False
        except Exception as e:
            logger.warning(f"Failed to check embedding table: {e}")
            return False

    def _store_embeddings(self, db, signals: list[dict]) -> int:
        """
        Generate and store embeddings for signals.

        Args:
            db: Database session
            signals: List of signal dicts with signal_id, title, summary

        Returns:
            Number of embeddings stored
        """
        if not signals:
            return 0

        # Check if embedding table exists (pgvector must be installed)
        if not self._check_embedding_table_exists(db):
            logger.info("Skipping embeddings: rkyc_signal_embedding table not found (pgvector not installed)")
            return 0

        logger.info(f"Generating embeddings for {len(signals)} signals")

        try:
            # Prepare texts for batch embedding
            texts = []
            for sig in signals:
                combined_text = f"""
Signal Type: {sig.get('signal_type', '')}
Event Type: {sig.get('event_type', '')}
Title: {sig.get('title', '')}
Summary: {sig.get('summary', '')}
""".strip()
                texts.append(combined_text)

            # Generate embeddings in batch
            embeddings = self.embedding_service.embed_batch(texts)

            # Store embeddings
            stored_count = 0
            for i, (sig, embedding) in enumerate(zip(signals, embeddings)):
                if embedding is None:
                    logger.warning(f"Failed to generate embedding for signal {sig['signal_id']}")
                    continue

                try:
                    # Insert into rkyc_signal_embedding
                    # Using raw SQL for vector type
                    # Note: Use CAST() instead of :: to avoid SQLAlchemy parameter binding conflicts
                    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
                    stmt = text("""
                        INSERT INTO rkyc_signal_embedding (embedding_id, signal_id, embedding, model_name)
                        VALUES (:embedding_id, :signal_id, CAST(:embedding AS vector), :model_name)
                        ON CONFLICT (signal_id) DO UPDATE SET
                            embedding = EXCLUDED.embedding,
                            model_name = EXCLUDED.model_name
                    """)
                    db.execute(stmt, {
                        "embedding_id": str(uuid4()),
                        "signal_id": sig["signal_id"],
                        "embedding": embedding_str,
                        "model_name": "text-embedding-3-large",
                    })
                    stored_count += 1
                except Exception as e:
                    logger.error(f"Failed to store embedding for signal {sig['signal_id']}: {e}")
                    continue

            logger.info(f"Stored {stored_count} embeddings")
            return stored_count

        except EmbeddingError as e:
            logger.error(f"Embedding generation failed: {e}")
            return 0
        except Exception as e:
            logger.error(f"Unexpected error storing embeddings: {e}")
            return 0

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

        # Create Signal with explicit enum conversion
        signal_id = uuid4()
        signal = Signal(
            signal_id=signal_id,
            corp_id=corp_id,
            signal_type=_safe_enum_convert(SignalType, signal_data["signal_type"], SignalType.DIRECT),
            event_type=_safe_enum_convert(EventType, signal_data["event_type"], EventType.KYC_REFRESH),
            event_signature=event_signature,
            snapshot_version=signal_data.get("snapshot_version", 0),
            impact_direction=_safe_enum_convert(ImpactDirection, signal_data["impact_direction"], ImpactDirection.NEUTRAL),
            impact_strength=_safe_enum_convert(ImpactStrength, signal_data["impact_strength"], ImpactStrength.MED),
            confidence=_safe_enum_convert(ConfidenceLevel, signal_data["confidence"], ConfidenceLevel.MED),
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

        # Create SignalIndex (denormalized for dashboard) with explicit enum conversion
        index = SignalIndex(
            index_id=uuid4(),
            corp_id=corp_id,
            corp_name=context.get("corp_name", ""),
            industry_code=context.get("industry_code", ""),
            signal_type=_safe_enum_convert(SignalType, signal_data["signal_type"], SignalType.DIRECT),
            event_type=_safe_enum_convert(EventType, signal_data["event_type"], EventType.KYC_REFRESH),
            impact_direction=_safe_enum_convert(ImpactDirection, signal_data["impact_direction"], ImpactDirection.NEUTRAL),
            impact_strength=_safe_enum_convert(ImpactStrength, signal_data["impact_strength"], ImpactStrength.MED),
            confidence=_safe_enum_convert(ConfidenceLevel, signal_data["confidence"], ConfidenceLevel.MED),
            title=signal_data.get("title", signal_data["summary"][:50]),
            summary_short=signal_data["summary"][:200],
            evidence_count=evidence_count,
            detected_at=datetime.now(UTC),
            signal_id=signal_id,
        )
        db.add(index)

        logger.debug(f"Created signal {signal_id} with {evidence_count} evidence items")
        return str(signal_id)
