"""
rKYC Analysis Pipeline Tasks
Main Celery tasks for corporate risk analysis
"""

import logging
from datetime import datetime, UTC
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
from app.worker.llm.exceptions import (
    RateLimitError,
    TimeoutError as LLMTimeoutError,
    AllProvidersFailedError,
)
from app.worker.pipelines.corp_profiling import get_corp_profiling_pipeline

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
                update_data["started_at"] = datetime.now(UTC)

        if status in (JobStatus.DONE, JobStatus.FAILED):
            update_data["finished_at"] = datetime.now(UTC)

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


def _save_profile_sync(profile: dict) -> None:
    """
    Save corp profile to database using sync session.

    This is called after async profiling pipeline completes,
    since the pipeline itself doesn't have a sync db session.
    """
    import json
    from sqlalchemy import text

    try:
        with get_sync_db() as db:
            # Upsert (insert or update) - using CAST instead of :: for SQLAlchemy compatibility
            query = text("""
                INSERT INTO rkyc_corp_profile (
                    profile_id, corp_id, business_summary, revenue_krw, export_ratio_pct,
                    country_exposure, key_materials, key_customers, overseas_operations,
                    profile_confidence, field_confidences, source_urls,
                    raw_search_result, field_provenance, extraction_model, extraction_prompt_version,
                    is_fallback, search_failed, validation_warnings, status,
                    fetched_at, expires_at
                ) VALUES (
                    CAST(:profile_id AS uuid), :corp_id, :business_summary, :revenue_krw, :export_ratio_pct,
                    CAST(:country_exposure AS jsonb), :key_materials, :key_customers, :overseas_operations,
                    CAST(:profile_confidence AS confidence_level), CAST(:field_confidences AS jsonb), :source_urls,
                    CAST(:raw_search_result AS jsonb), CAST(:field_provenance AS jsonb), :extraction_model, :extraction_prompt_version,
                    :is_fallback, :search_failed, :validation_warnings, :status,
                    CAST(:fetched_at AS timestamptz), CAST(:expires_at AS timestamptz)
                )
                ON CONFLICT (corp_id) DO UPDATE SET
                    business_summary = EXCLUDED.business_summary,
                    revenue_krw = EXCLUDED.revenue_krw,
                    export_ratio_pct = EXCLUDED.export_ratio_pct,
                    country_exposure = EXCLUDED.country_exposure,
                    key_materials = EXCLUDED.key_materials,
                    key_customers = EXCLUDED.key_customers,
                    overseas_operations = EXCLUDED.overseas_operations,
                    profile_confidence = EXCLUDED.profile_confidence,
                    field_confidences = EXCLUDED.field_confidences,
                    source_urls = EXCLUDED.source_urls,
                    raw_search_result = EXCLUDED.raw_search_result,
                    field_provenance = EXCLUDED.field_provenance,
                    extraction_model = EXCLUDED.extraction_model,
                    extraction_prompt_version = EXCLUDED.extraction_prompt_version,
                    is_fallback = EXCLUDED.is_fallback,
                    search_failed = EXCLUDED.search_failed,
                    validation_warnings = EXCLUDED.validation_warnings,
                    status = EXCLUDED.status,
                    fetched_at = EXCLUDED.fetched_at,
                    expires_at = EXCLUDED.expires_at,
                    updated_at = NOW()
            """)

            db.execute(query, {
                "profile_id": str(profile.get("profile_id", "")),
                "corp_id": profile.get("corp_id", ""),
                "business_summary": profile.get("business_summary"),
                "revenue_krw": profile.get("revenue_krw"),
                "export_ratio_pct": profile.get("export_ratio_pct"),
                "country_exposure": json.dumps(profile.get("country_exposure", {})),
                "key_materials": profile.get("key_materials", []),
                "key_customers": profile.get("key_customers", []),
                "overseas_operations": profile.get("overseas_operations", []),
                "profile_confidence": profile.get("profile_confidence", "LOW"),
                "field_confidences": json.dumps(profile.get("field_confidences", {})),
                "source_urls": profile.get("source_urls", []),
                "raw_search_result": json.dumps(profile.get("raw_search_result", {})),
                "field_provenance": json.dumps(profile.get("field_provenance", {})),
                "extraction_model": profile.get("extraction_model"),
                "extraction_prompt_version": profile.get("extraction_prompt_version"),
                "is_fallback": profile.get("is_fallback", False),
                "search_failed": profile.get("search_failed", False),
                "validation_warnings": profile.get("validation_warnings", []),
                "status": profile.get("status", "ACTIVE"),
                "fetched_at": profile.get("fetched_at"),
                "expires_at": profile.get("expires_at"),
            })
            db.commit()
            logger.info(f"Saved profile for corp_id={profile.get('corp_id')}")

    except Exception as e:
        logger.error(f"Failed to save profile: {e}")
        # Don't raise - profile save failure shouldn't stop the pipeline


@celery_app.task(
    bind=True,
    name="run_analysis_pipeline",
    # Only retry on transient errors (rate limits, timeouts, provider failures)
    # Business logic errors (ValueError, KeyError) should NOT be retried
    autoretry_for=(RateLimitError, LLMTimeoutError, AllProvidersFailedError, ConnectionError, TimeoutError),
    retry_kwargs={"max_retries": 3, "countdown": 60},
    retry_backoff=True,
    retry_backoff_max=300,
)
def run_analysis_pipeline(self, job_id: str, corp_id: str):
    """
    Main analysis pipeline orchestrator.

    9-Stage Pipeline:
    1. SNAPSHOT - Collect internal snapshot data
    2. DOC_INGEST - Parse submitted documents
    3. PROFILING - Corp profiling for ENVIRONMENT signal enhancement (NEW)
    4. EXTERNAL - Search external news/events
    5. UNIFIED_CONTEXT - Build unified context
    6. SIGNAL - Extract risk signals using LLM
    7. VALIDATION - Apply guardrails
    8. INDEX - Save to database
    9. INSIGHT - Generate final briefing
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

        # Stage 3: PROFILING (Corp profiling for ENVIRONMENT signal grounding)
        update_job_progress(job_id, JobStatus.RUNNING, ProgressStep.PROFILING, 28)
        corp_name = snapshot_data.get("corporation", {}).get("corp_name", "")
        industry_code = snapshot_data.get("corporation", {}).get("industry_code", "")

        # Run async profiling pipeline in sync context (Celery-safe)
        import asyncio
        profiling_pipeline = get_corp_profiling_pipeline()
        try:
            # Check if event loop is already running (e.g., nested async context)
            try:
                loop = asyncio.get_running_loop()
                # If we get here, there's already a running loop - use thread executor
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        profiling_pipeline.execute(
                            corp_id=corp_id,
                            corp_name=corp_name,
                            industry_code=industry_code,
                            db_session=None,
                            llm_service=signal_pipeline.llm_service if hasattr(signal_pipeline, 'llm_service') else None,
                        )
                    )
                    profile_result = future.result(timeout=120)  # 2 min timeout
            except RuntimeError:
                # No running loop - safe to create new one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    profile_result = loop.run_until_complete(
                        profiling_pipeline.execute(
                            corp_id=corp_id,
                            corp_name=corp_name,
                            industry_code=industry_code,
                            db_session=None,
                            llm_service=signal_pipeline.llm_service if hasattr(signal_pipeline, 'llm_service') else None,
                        )
                    )
                finally:
                    loop.close()
            logger.info(
                f"PROFILING completed: confidence={profile_result.profile.get('profile_confidence')}, "
                f"queries_selected={len(profile_result.selected_queries)}, "
                f"is_cached={profile_result.is_cached}"
            )
            # Store profile data for context building
            profile_data = {
                "profile": profile_result.profile,
                "selected_queries": profile_result.selected_queries,
                "query_details": profile_result.query_details,
            }

            # Save profile to DB using sync session (async pipeline doesn't have db_session)
            if profile_result.profile:
                _save_profile_sync(profile_result.profile)

        except Exception as e:
            # PROFILING failure should not stop the pipeline
            logger.warning(f"PROFILING stage failed (non-fatal): {e}")
            profile_data = {
                "profile": None,
                "selected_queries": [],
                "query_details": [],
            }
        update_job_progress(job_id, JobStatus.RUNNING, ProgressStep.PROFILING, 32)

        # Stage 4: EXTERNAL (Perplexity search if API key configured)
        update_job_progress(job_id, JobStatus.RUNNING, ProgressStep.EXTERNAL, 35)
        external_data = external_pipeline.execute(corp_name, industry_code, corp_id)
        # Attach profile data to external_data for context pipeline
        external_data["profile_data"] = profile_data
        update_job_progress(job_id, JobStatus.RUNNING, ProgressStep.EXTERNAL, 42)

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
