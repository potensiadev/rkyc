"""
rKYC Scheduled Tasks
Periodic background tasks for automated signal detection
"""

import logging
from datetime import datetime, UTC, timedelta
from uuid import uuid4

from sqlalchemy import text

from app.worker.celery_app import celery_app
from app.worker.db import get_sync_db
from app.worker.tasks.analysis import run_analysis_pipeline

logger = logging.getLogger(__name__)


@celery_app.task(name="scan_all_corporations")
def scan_all_corporations():
    """
    Scan all active corporations for new signals.
    Triggered periodically by Celery Beat.

    This task:
    1. Fetches all corporations from the database
    2. Creates an analysis job for each corporation
    3. Queues the analysis pipeline
    """
    logger.info("Starting scheduled scan of all corporations")

    try:
        with get_sync_db() as db:
            # Get all corporations
            result = db.execute(text("""
                SELECT corp_id, corp_name
                FROM corp
                ORDER BY corp_id
            """))
            corporations = result.fetchall()

            jobs_created = 0
            for corp in corporations:
                corp_id = corp[0]
                corp_name = corp[1]

                # Check if there's already a recent job (within last hour)
                recent_job = db.execute(text("""
                    SELECT job_id FROM rkyc_job
                    WHERE corp_id = :corp_id
                      AND status IN ('QUEUED', 'RUNNING')
                      AND queued_at > :cutoff
                    LIMIT 1
                """), {
                    "corp_id": corp_id,
                    "cutoff": datetime.now(UTC) - timedelta(hours=1)
                }).fetchone()

                if recent_job:
                    logger.debug(f"Skipping {corp_name} - recent job exists")
                    continue

                # Create new job
                job_id = str(uuid4())
                db.execute(text("""
                    INSERT INTO rkyc_job (job_id, job_type, corp_id, status, queued_at, progress_percent)
                    VALUES (:job_id, 'ANALYZE', :corp_id, 'QUEUED', :queued_at, 0)
                """), {
                    "job_id": job_id,
                    "corp_id": corp_id,
                    "queued_at": datetime.now(UTC)
                })
                db.commit()

                # Queue the analysis task
                run_analysis_pipeline.delay(job_id, corp_id)
                jobs_created += 1
                logger.info(f"Queued analysis job for {corp_name} (job_id={job_id[:8]}...)")

            logger.info(f"Scheduled scan complete: {jobs_created} jobs created for {len(corporations)} corporations")
            return {
                "status": "success",
                "corporations_scanned": len(corporations),
                "jobs_created": jobs_created
            }

    except Exception as e:
        logger.error(f"Scheduled scan failed: {str(e)}")
        raise


@celery_app.task(name="scan_single_corporation")
def scan_single_corporation(corp_id: str):
    """
    Scan a single corporation for new signals.
    Can be triggered manually or by external events.
    """
    logger.info(f"Starting scan for corporation: {corp_id}")

    try:
        with get_sync_db() as db:
            # Verify corporation exists
            result = db.execute(text("""
                SELECT corp_name FROM corp WHERE corp_id = :corp_id
            """), {"corp_id": corp_id})
            corp = result.fetchone()

            if not corp:
                logger.error(f"Corporation not found: {corp_id}")
                return {"status": "error", "message": "Corporation not found"}

            # Create new job
            job_id = str(uuid4())
            db.execute(text("""
                INSERT INTO rkyc_job (job_id, job_type, corp_id, status, queued_at, progress_percent)
                VALUES (:job_id, 'ANALYZE', :corp_id, 'QUEUED', :queued_at, 0)
            """), {
                "job_id": job_id,
                "corp_id": corp_id,
                "queued_at": datetime.now(UTC)
            })
            db.commit()

            # Queue the analysis task
            run_analysis_pipeline.delay(job_id, corp_id)

            logger.info(f"Queued analysis for {corp[0]} (job_id={job_id[:8]}...)")
            return {
                "status": "success",
                "job_id": job_id,
                "corp_id": corp_id
            }

    except Exception as e:
        logger.error(f"Single corporation scan failed: {str(e)}")
        raise


@celery_app.task(name="scan_high_risk_corporations")
def scan_high_risk_corporations():
    """
    Scan only high-risk corporations more frequently.
    These are corporations with:
    - Recent HIGH impact signals
    - HIGH internal risk grade
    - Recent overdue flags
    """
    logger.info("Starting high-risk corporation scan")

    try:
        with get_sync_db() as db:
            # Find high-risk corporations
            result = db.execute(text("""
                SELECT DISTINCT c.corp_id, c.corp_name
                FROM corp c
                LEFT JOIN rkyc_signal_index si ON c.corp_id = si.corp_id
                LEFT JOIN rkyc_internal_snapshot_latest isl ON c.corp_id = isl.corp_id
                LEFT JOIN rkyc_internal_snapshot snap ON isl.snapshot_id = snap.snapshot_id
                WHERE
                    -- Has recent HIGH impact signals
                    (si.impact_strength = 'HIGH' AND si.detected_at > NOW() - INTERVAL '7 days')
                    -- Or has HIGH internal risk grade
                    OR (snap.snapshot_json->>'corp'->>'kyc_status'->>'internal_risk_grade' = 'HIGH')
                ORDER BY c.corp_id
            """))
            high_risk_corps = result.fetchall()

            jobs_created = 0
            for corp in high_risk_corps:
                corp_id = corp[0]

                # Check for existing recent job
                recent_job = db.execute(text("""
                    SELECT job_id FROM rkyc_job
                    WHERE corp_id = :corp_id
                      AND status IN ('QUEUED', 'RUNNING')
                      AND queued_at > :cutoff
                    LIMIT 1
                """), {
                    "corp_id": corp_id,
                    "cutoff": datetime.now(UTC) - timedelta(minutes=30)
                }).fetchone()

                if recent_job:
                    continue

                # Create and queue job
                job_id = str(uuid4())
                db.execute(text("""
                    INSERT INTO rkyc_job (job_id, job_type, corp_id, status, queued_at, progress_percent)
                    VALUES (:job_id, 'ANALYZE', :corp_id, 'QUEUED', :queued_at, 0)
                """), {
                    "job_id": job_id,
                    "corp_id": corp_id,
                    "queued_at": datetime.now(UTC)
                })
                db.commit()

                run_analysis_pipeline.delay(job_id, corp_id)
                jobs_created += 1

            logger.info(f"High-risk scan complete: {jobs_created} jobs for {len(high_risk_corps)} high-risk corporations")
            return {
                "status": "success",
                "high_risk_corporations": len(high_risk_corps),
                "jobs_created": jobs_created
            }

    except Exception as e:
        logger.error(f"High-risk scan failed: {str(e)}")
        raise


@celery_app.task(name="cleanup_old_jobs")
def cleanup_old_jobs(days: int = 30):
    """
    Clean up old completed/failed jobs from the database.
    Keeps the database lean and improves query performance.
    """
    logger.info(f"Starting cleanup of jobs older than {days} days")

    try:
        with get_sync_db() as db:
            cutoff = datetime.now(UTC) - timedelta(days=days)

            result = db.execute(text("""
                DELETE FROM rkyc_job
                WHERE status IN ('DONE', 'FAILED')
                  AND finished_at < :cutoff
                RETURNING job_id
            """), {"cutoff": cutoff})

            deleted_count = len(result.fetchall())
            db.commit()

            logger.info(f"Cleanup complete: {deleted_count} old jobs deleted")
            return {
                "status": "success",
                "jobs_deleted": deleted_count
            }

    except Exception as e:
        logger.error(f"Job cleanup failed: {str(e)}")
        raise
