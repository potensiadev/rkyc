"""
Document Ingest Pipeline Stage
Stage 2: DOC_INGEST - Vision LLM based document processing
"""

import base64
import hashlib
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from sqlalchemy import select, update

from app.worker.db import get_sync_db
from app.worker.llm.service import LLMService
from app.worker.llm.prompts import DOC_EXTRACTION_SYSTEM, get_doc_extraction_prompt
from app.worker.llm.exceptions import AllProvidersFailedError
from app.models.document import (
    Document, DocumentPage, Fact,
    DocType, IngestStatus, ConfidenceLevel
)

logger = logging.getLogger(__name__)


class DocumentNotFoundError(Exception):
    """Raised when document is not found"""
    pass


class DocumentProcessingError(Exception):
    """Raised when document processing fails"""
    pass


class DocIngestPipeline:
    """
    Stage 2: DOC_INGEST - Vision LLM based document processing

    Supported document types (PRD 6.2):
    - BIZ_REG: 사업자등록증
    - REGISTRY: 법인 등기부등본
    - SHAREHOLDERS: 주주명부
    - AOI: 정관
    - FIN_STATEMENT: 재무제표 요약

    Processing flow:
    1. Query rkyc_document for corp_id's documents
    2. For each document with PENDING/FAILED status:
       a. Load document image (from storage_path or base64)
       b. Send to Vision LLM with doc-type specific prompt
       c. Parse extracted facts
       d. Save to rkyc_fact table
       e. Update ingest_status to DONE
    3. Return aggregated document data for context
    """

    def __init__(self):
        self.llm = LLMService()

    def execute(self, corp_id: str) -> dict:
        """
        Execute document ingest stage.

        Args:
            corp_id: Corporation ID to process documents for

        Returns:
            dict: Aggregated document data for unified context
            {
                "documents_processed": 2,
                "facts_extracted": 15,
                "doc_summaries": {
                    "BIZ_REG": {"biz_no": "123-45-67890", ...},
                    "SHAREHOLDERS": {"shareholders": [...], ...}
                }
            }
        """
        logger.info(f"DOC_INGEST stage starting for corp_id={corp_id}")

        result = {
            "documents_processed": 0,
            "facts_extracted": 0,
            "doc_summaries": {},
            "errors": [],
        }

        with get_sync_db() as db:
            # Get all documents for this corporation
            documents = db.execute(
                select(Document).where(Document.corp_id == corp_id)
            ).scalars().all()

            if not documents:
                logger.info(f"No documents found for corp_id={corp_id}")
                return result

            logger.info(f"Found {len(documents)} documents for corp_id={corp_id}")

            for doc in documents:
                # Skip already processed documents (unless re-processing is needed)
                if doc.ingest_status == IngestStatus.DONE:
                    # Check if file_hash changed (document updated)
                    if not self._needs_reprocessing(doc):
                        logger.debug(f"Skipping already processed doc {doc.doc_id}")
                        # Still include in summaries if facts exist
                        facts = self._get_existing_facts(db, doc.doc_id)
                        if facts:
                            result["doc_summaries"][doc.doc_type.value] = self._facts_to_summary(facts)
                        continue

                try:
                    # Process document
                    facts_data = self._process_document(db, doc, corp_id)

                    if facts_data:
                        result["documents_processed"] += 1
                        result["facts_extracted"] += len(facts_data.get("facts", []))
                        result["doc_summaries"][doc.doc_type.value] = self._facts_to_summary(
                            facts_data.get("facts", [])
                        )

                except DocumentProcessingError as e:
                    logger.error(f"Failed to process document {doc.doc_id}: {e}")
                    result["errors"].append({
                        "doc_id": str(doc.doc_id),
                        "doc_type": doc.doc_type.value,
                        "error": str(e),
                    })
                    # Mark document as failed
                    self._update_document_status(db, doc.doc_id, IngestStatus.FAILED)

                except Exception as e:
                    logger.error(f"Unexpected error processing document {doc.doc_id}: {e}")
                    result["errors"].append({
                        "doc_id": str(doc.doc_id),
                        "doc_type": doc.doc_type.value,
                        "error": str(e),
                    })
                    self._update_document_status(db, doc.doc_id, IngestStatus.FAILED)

            db.commit()

        logger.info(
            f"DOC_INGEST stage completed: "
            f"processed={result['documents_processed']}, "
            f"facts={result['facts_extracted']}, "
            f"errors={len(result['errors'])}"
        )

        return result

    def _needs_reprocessing(self, doc: Document) -> bool:
        """
        Check if document needs reprocessing based on file_hash change.

        Returns True if document should be reprocessed.
        """
        # If no file_hash stored, assume needs processing
        if not doc.file_hash:
            return True

        # If storage_path exists, compute current hash and compare
        if doc.storage_path:
            try:
                current_hash = self._compute_file_hash(doc.storage_path)
                return current_hash != doc.file_hash
            except Exception:
                return False

        return False

    def _compute_file_hash(self, file_path: str) -> str:
        """Compute SHA256 hash of file"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        sha256_hash = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    def _process_document(self, db, doc: Document, corp_id: str) -> Optional[dict]:
        """
        Process a single document using Vision LLM.

        Returns:
            dict with extracted facts, or None if processing failed
        """
        logger.info(f"Processing document {doc.doc_id} (type={doc.doc_type.value})")

        # Update status to RUNNING
        self._update_document_status(db, doc.doc_id, IngestStatus.RUNNING)

        # Load document image
        image_base64 = self._load_document_image(doc)
        if not image_base64:
            raise DocumentProcessingError(f"Failed to load image for document {doc.doc_id}")

        # Get extraction prompt for this document type
        system_prompt = DOC_EXTRACTION_SYSTEM
        user_prompt = get_doc_extraction_prompt(doc.doc_type.value)

        start_time = time.time()

        try:
            # Call Vision LLM for extraction
            extraction_result = self.llm.extract_document_facts(
                image_base64=image_base64,
                doc_type=doc.doc_type.value,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )

            extraction_time_ms = int((time.time() - start_time) * 1000)
            logger.info(f"Vision LLM extraction completed in {extraction_time_ms}ms")

            # Parse and save facts
            facts = extraction_result.get("facts", [])
            saved_facts = self._save_facts(db, doc, corp_id, facts)

            # Update document status to DONE
            self._update_document_status(db, doc.doc_id, IngestStatus.DONE)

            # Update last_ingested_at
            db.execute(
                update(Document)
                .where(Document.doc_id == doc.doc_id)
                .values(last_ingested_at=datetime.utcnow())
            )

            return {
                "doc_type": doc.doc_type.value,
                "facts": saved_facts,
                "extraction_time_ms": extraction_time_ms,
            }

        except AllProvidersFailedError as e:
            logger.error(f"Vision LLM failed for document {doc.doc_id}: {e}")
            raise DocumentProcessingError(f"Vision LLM extraction failed: {e}")

    def _load_document_image(self, doc: Document) -> Optional[str]:
        """
        Load document image and return base64 encoded string.

        Supports:
        - Local file path (storage_path)
        - First page of multi-page document
        """
        if doc.storage_path:
            try:
                path = Path(doc.storage_path)
                if path.exists():
                    with open(path, "rb") as f:
                        return base64.b64encode(f.read()).decode("utf-8")
            except Exception as e:
                logger.error(f"Failed to read document file: {e}")

        # If no storage_path, check document pages
        # (For demo/test, pages might have image_path)
        # This is a placeholder for actual implementation

        return None

    def _save_facts(
        self,
        db,
        doc: Document,
        corp_id: str,
        facts: list[dict],
    ) -> list[dict]:
        """
        Save extracted facts to rkyc_fact table.

        Args:
            db: Database session
            doc: Document being processed
            corp_id: Corporation ID
            facts: List of extracted fact dicts from LLM

        Returns:
            List of saved fact dicts
        """
        # First, delete existing facts for this document
        # (to handle re-processing)
        db.execute(
            Fact.__table__.delete().where(Fact.doc_id == doc.doc_id)
        )

        saved_facts = []

        for fact_data in facts:
            try:
                # Parse confidence level
                confidence_str = fact_data.get("confidence", "MED")
                try:
                    confidence = ConfidenceLevel(confidence_str)
                except ValueError:
                    confidence = ConfidenceLevel.MED

                # Determine value type and store appropriately
                field_value = fact_data.get("field_value")
                field_value_text = None
                field_value_num = None
                field_value_json = None

                if isinstance(field_value, str):
                    field_value_text = field_value
                elif isinstance(field_value, (int, float)):
                    field_value_num = field_value
                elif isinstance(field_value, (dict, list)):
                    field_value_json = field_value
                else:
                    field_value_text = str(field_value) if field_value else None

                # Create fact record
                fact = Fact(
                    fact_id=uuid4(),
                    corp_id=corp_id,
                    doc_id=doc.doc_id,
                    doc_type=doc.doc_type,
                    fact_type=fact_data.get("fact_type", "UNKNOWN"),
                    field_key=fact_data.get("field_key", "unknown"),
                    field_value_text=field_value_text,
                    field_value_num=field_value_num,
                    field_value_json=field_value_json,
                    confidence=confidence,
                    evidence_snippet=fact_data.get("evidence_snippet", "")[:400],
                    evidence_page_no=fact_data.get("page_no", 1),
                    extracted_by="vision-llm",
                    extracted_at=datetime.utcnow(),
                )
                db.add(fact)

                saved_facts.append({
                    "fact_type": fact.fact_type,
                    "field_key": fact.field_key,
                    "field_value": field_value,
                    "confidence": confidence.value,
                })

            except Exception as e:
                logger.error(f"Failed to save fact: {e}")
                continue

        logger.info(f"Saved {len(saved_facts)} facts for document {doc.doc_id}")
        return saved_facts

    def _update_document_status(self, db, doc_id, status: IngestStatus):
        """Update document ingest status"""
        db.execute(
            update(Document)
            .where(Document.doc_id == doc_id)
            .values(ingest_status=status)
        )

    def _get_existing_facts(self, db, doc_id) -> list[dict]:
        """Get existing facts for a document"""
        facts = db.execute(
            select(Fact).where(Fact.doc_id == doc_id)
        ).scalars().all()

        return [
            {
                "fact_type": f.fact_type,
                "field_key": f.field_key,
                "field_value": f.field_value_text or f.field_value_num or f.field_value_json,
                "confidence": f.confidence.value if f.confidence else "MED",
            }
            for f in facts
        ]

    def _facts_to_summary(self, facts: list[dict]) -> dict:
        """
        Convert list of facts to summary dict.

        Groups facts by fact_type and field_key.
        """
        summary = {}

        for fact in facts:
            field_key = fact.get("field_key", "unknown")
            field_value = fact.get("field_value")

            # Use field_key as key, value as value
            summary[field_key] = field_value

        return summary

    def process_single_document(
        self,
        corp_id: str,
        doc_type: str,
        image_base64: str,
        page_no: int = 1,
    ) -> dict:
        """
        Process a single document image directly (for API endpoint).

        This method bypasses the document storage and processes
        the image directly. Useful for testing and manual uploads.

        Args:
            corp_id: Corporation ID
            doc_type: Document type (BIZ_REG, REGISTRY, etc.)
            image_base64: Base64 encoded image
            page_no: Page number (default 1)

        Returns:
            dict with extracted facts
        """
        logger.info(f"Processing single document: corp_id={corp_id}, type={doc_type}")

        # Validate doc_type
        try:
            DocType(doc_type)
        except ValueError:
            raise ValueError(f"Invalid document type: {doc_type}")

        system_prompt = DOC_EXTRACTION_SYSTEM
        user_prompt = get_doc_extraction_prompt(doc_type)

        start_time = time.time()

        try:
            extraction_result = self.llm.extract_document_facts(
                image_base64=image_base64,
                doc_type=doc_type,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )

            extraction_time_ms = int((time.time() - start_time) * 1000)

            return {
                "doc_type": doc_type,
                "facts": extraction_result.get("facts", []),
                "extraction_time_ms": extraction_time_ms,
                "model_used": "vision-llm",
            }

        except AllProvidersFailedError as e:
            raise DocumentProcessingError(f"Vision LLM extraction failed: {e}")
