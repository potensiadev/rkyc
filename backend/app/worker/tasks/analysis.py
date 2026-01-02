"""
rKYC Analysis Pipeline Tasks
Main Celery tasks for corporate risk analysis
"""

import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import update

from app.worker.celery_app import celery_app
from app.worker.db import get_sync_db
from app.models.job import Job, JobStatus, ProgressStep
from app.worker.pipelines import (
    SnapshotPipeline,
    DocIngestPipeline,
    ContextPipeline,
    ExternalSearchPipeline,
    SignalExtractionPipeline,
    ValidationPipeline,
    DeduplicationPipeline,
    deduplicate_within_batch,
    IndexPipeline,
    InsightPipeline,
    NoSnapshotError,
    NoCorporationError,
)

logger = logging.getLogger(__name__)


def update_job_progress(
    job_id: str,
    status: JobStatus,
    step: ProgressStep = None,
    percent: int = 0,
    error_code: str = None,
    error_message: str = None,
):
    """Update job progress in database"""
    with get_sync_db() as db:
        update_data = {
            "status": status.value,
            "progress_percent": percent,
        }

        if step:
            update_data["progress_step"] = step.value

        if status == JobStatus.RUNNING:
            # Set started_at if not already set
            job = db.execute(
                Job.__table__.select().where(Job.job_id == UUID(job_id))
            ).fetchone()
            if job and not job.started_at:
                update_data["started_at"] = datetime.utcnow()

        if status in (JobStatus.DONE, JobStatus.FAILED):
            update_data["finished_at"] = datetime.utcnow()

        if error_code:
            update_data["error_code"] = error_code
        if error_message:
            update_data["error_message"] = error_message

        stmt = (
            update(Job)
            .where(Job.job_id == UUID(job_id))
            .values(**update_data)
        )
        db.execute(stmt)
        db.commit()

        logger.info(f"Job {job_id} updated: status={status.value}, step={step}, percent={percent}")


@celery_app.task(
    bind=True,
    name="run_analysis_pipeline",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 60},
    retry_backoff=True,
    retry_backoff_max=300,
)
def run_analysis_pipeline(self, job_id: str, corp_id: str):
    """
    Main analysis pipeline orchestrator.

    8-Stage Pipeline:
    1. SNAPSHOT - Collect internal snapshot data
    2. DOC_INGEST - Parse submitted documents (skipped for now)
    3. EXTERNAL - Search external news/events (Phase 5)
    4. UNIFIED_CONTEXT - Build unified context
    5. SIGNAL - Extract risk signals using LLM
    6. VALIDATION - Apply guardrails (Phase 4)
    7. INDEX - Save to database
    8. INSIGHT - Generate final briefing (Phase 5)
    """
    logger.info(f"Starting analysis pipeline for job={job_id}, corp_id={corp_id}")

    # Initialize pipelines
    snapshot_pipeline = SnapshotPipeline()
    doc_ingest_pipeline = DocIngestPipeline()
    external_pipeline = ExternalSearchPipeline()
    context_pipeline = ContextPipeline()
    signal_pipeline = SignalExtractionPipeline()
    validation_pipeline = ValidationPipeline()
    dedup_pipeline = DeduplicationPipeline()
    index_pipeline = IndexPipeline()
    insight_pipeline = InsightPipeline()

    try:
        # Stage 1: SNAPSHOT
        update_job_progress(job_id, JobStatus.RUNNING, ProgressStep.SNAPSHOT, 5)
        try:
            snapshot_data = snapshot_pipeline.execute(corp_id)
        except (NoSnapshotError, NoCorporationError) as e:
            logger.error(f"Snapshot stage failed: {e}")
            update_job_progress(
                job_id,
                JobStatus.FAILED,
                ProgressStep.SNAPSHOT,
                error_code="SNAPSHOT_ERROR",
                error_message=str(e),
            )
            return {"status": "failed", "error": str(e)}
        update_job_progress(job_id, JobStatus.RUNNING, ProgressStep.SNAPSHOT, 15)

        # Stage 2: DOC_INGEST (Vision LLM document processing)
        update_job_progress(job_id, JobStatus.RUNNING, ProgressStep.DOC_INGEST, 20)
        try:
            doc_data = doc_ingest_pipeline.execute(corp_id)
            logger.info(
                f"DOC_INGEST completed: docs={doc_data.get('documents_processed', 0)}, "
                f"facts={doc_data.get('facts_extracted', 0)}"
            )
        except Exception as e:
            # DOC_INGEST failure should not stop the pipeline
            logger.warning(f"DOC_INGEST stage failed (non-fatal): {e}")
            doc_data = {"documents_processed": 0, "facts_extracted": 0, "doc_summaries": {}}
        update_job_progress(job_id, JobStatus.RUNNING, ProgressStep.DOC_INGEST, 25)

        # Stage 3: EXTERNAL (Perplexity search if API key configured)
        update_job_progress(job_id, JobStatus.RUNNING, ProgressStep.EXTERNAL, 30)
        corp_name = snapshot_data.get("corporation", {}).get("corp_name", "")
        industry_name = snapshot_data.get("corporation", {}).get("industry_code", "")
        external_data = external_pipeline.execute(corp_name, industry_name, corp_id)
        update_job_progress(job_id, JobStatus.RUNNING, ProgressStep.EXTERNAL, 40)

        # Stage 4: UNIFIED_CONTEXT
        update_job_progress(job_id, JobStatus.RUNNING, ProgressStep.UNIFIED_CONTEXT, 45)
        context = context_pipeline.execute(snapshot_data, doc_data, external_data)
        update_job_progress(job_id, JobStatus.RUNNING, ProgressStep.UNIFIED_CONTEXT, 50)

        # Stage 5: SIGNAL (LLM extraction)
        update_job_progress(job_id, JobStatus.RUNNING, ProgressStep.SIGNAL, 55)
        raw_signals = signal_pipeline.execute(context)
        update_job_progress(job_id, JobStatus.RUNNING, ProgressStep.SIGNAL, 65)

        # Stage 6: VALIDATION (guardrails + deduplication)
        update_job_progress(job_id, JobStatus.RUNNING, ProgressStep.VALIDATION, 70)
        # 6a. Remove intra-batch duplicates
        deduped_batch = deduplicate_within_batch(raw_signals)
        # 6b. Apply guardrails validation
        validated_signals = validation_pipeline.execute(deduped_batch)
        # 6c. Remove duplicates against existing DB signals
        validated_signals = dedup_pipeline.execute(validated_signals, corp_id)
        update_job_progress(job_id, JobStatus.RUNNING, ProgressStep.VALIDATION, 80)

        # Stage 7: INDEX
        update_job_progress(job_id, JobStatus.RUNNING, ProgressStep.INDEX, 85)
        signal_ids = index_pipeline.execute(validated_signals, context)
        update_job_progress(job_id, JobStatus.RUNNING, ProgressStep.INDEX, 90)

        # Stage 8: INSIGHT (LLM-based briefing generation)
        update_job_progress(job_id, JobStatus.RUNNING, ProgressStep.INSIGHT, 95)
        insight = insight_pipeline.execute(validated_signals, context)
        update_job_progress(job_id, JobStatus.DONE, ProgressStep.INSIGHT, 100)

        logger.info(f"Pipeline completed for job={job_id}, signals_created={len(signal_ids)}")

        return {
            "status": "success",
            "job_id": job_id,
            "corp_id": corp_id,
            "signals_created": len(signal_ids),
            "signal_ids": signal_ids,
        }

    except Exception as e:
        logger.error(f"Pipeline failed for job={job_id}: {str(e)}")
        update_job_progress(
            job_id,
            JobStatus.FAILED,
            error_code="PIPELINE_ERROR",
            error_message=str(e)[:500],
        )
        raise
