"""
Dynamic Scheduler for Demo Mode
Allows real-time control of scheduled tasks via API

This module provides:
- Start/Stop scheduler control
- Dynamic interval adjustment (1, 3, 5, 10 minutes)
- Status monitoring
"""

import logging
import threading
import time
from datetime import datetime, UTC
from enum import Enum
from typing import Optional
from uuid import uuid4

from sqlalchemy import text

from app.worker.celery_app import celery_app
from app.worker.db import get_sync_db
from app.worker.tasks.analysis import run_analysis_pipeline

logger = logging.getLogger(__name__)


class SchedulerStatus(str, Enum):
    STOPPED = "STOPPED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"


class DynamicScheduler:
    """
    Dynamic scheduler for real-time signal detection demo.

    This scheduler runs in a separate thread and can be controlled
    via API calls to start, stop, and change intervals.
    """

    _instance: Optional["DynamicScheduler"] = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern - only one scheduler instance allowed."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._status = SchedulerStatus.STOPPED
        self._interval_minutes = 5  # Default 5 minutes
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._last_run: Optional[datetime] = None
        self._next_run: Optional[datetime] = None
        self._total_runs = 0
        self._total_signals_detected = 0
        self._current_corp_index = 0
        self._corporations: list = []

        logger.info("DynamicScheduler initialized")

    @property
    def status(self) -> SchedulerStatus:
        return self._status

    @property
    def interval_minutes(self) -> int:
        return self._interval_minutes

    @property
    def last_run(self) -> Optional[datetime]:
        return self._last_run

    @property
    def next_run(self) -> Optional[datetime]:
        return self._next_run

    @property
    def total_runs(self) -> int:
        return self._total_runs

    @property
    def total_signals_detected(self) -> int:
        return self._total_signals_detected

    def start(self, interval_minutes: int = 5) -> dict:
        """
        Start the scheduler with the specified interval.

        Args:
            interval_minutes: Scan interval (1, 3, 5, or 10 minutes)

        Returns:
            Status dictionary
        """
        if self._status == SchedulerStatus.RUNNING:
            return {
                "status": "already_running",
                "interval_minutes": self._interval_minutes,
                "message": "Scheduler is already running"
            }

        # Validate interval
        valid_intervals = [1, 3, 5, 10]
        if interval_minutes not in valid_intervals:
            return {
                "status": "error",
                "message": f"Invalid interval. Must be one of {valid_intervals}"
            }

        self._interval_minutes = interval_minutes
        self._stop_event.clear()
        self._status = SchedulerStatus.RUNNING

        # Load corporations list
        self._load_corporations()

        # Start the scheduler thread
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

        logger.info(f"DynamicScheduler started with {interval_minutes} minute interval")

        return {
            "status": "started",
            "interval_minutes": interval_minutes,
            "corporations_count": len(self._corporations),
            "message": f"Scheduler started. Scanning every {interval_minutes} minutes."
        }

    def stop(self) -> dict:
        """Stop the scheduler."""
        if self._status == SchedulerStatus.STOPPED:
            return {
                "status": "already_stopped",
                "message": "Scheduler is not running"
            }

        self._stop_event.set()
        self._status = SchedulerStatus.STOPPED
        self._next_run = None

        # Wait for thread to finish
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

        logger.info("DynamicScheduler stopped")

        return {
            "status": "stopped",
            "total_runs": self._total_runs,
            "message": "Scheduler stopped"
        }

    def set_interval(self, interval_minutes: int) -> dict:
        """
        Change the scan interval while running.

        Args:
            interval_minutes: New interval (1, 3, 5, or 10 minutes)
        """
        valid_intervals = [1, 3, 5, 10]
        if interval_minutes not in valid_intervals:
            return {
                "status": "error",
                "message": f"Invalid interval. Must be one of {valid_intervals}"
            }

        old_interval = self._interval_minutes
        self._interval_minutes = interval_minutes

        logger.info(f"DynamicScheduler interval changed: {old_interval} -> {interval_minutes} minutes")

        return {
            "status": "updated",
            "old_interval": old_interval,
            "new_interval": interval_minutes,
            "message": f"Interval changed to {interval_minutes} minutes"
        }

    def get_status(self) -> dict:
        """Get current scheduler status."""
        return {
            "status": self._status.value,
            "interval_minutes": self._interval_minutes,
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "next_run": self._next_run.isoformat() if self._next_run else None,
            "total_runs": self._total_runs,
            "total_signals_detected": self._total_signals_detected,
            "corporations_count": len(self._corporations),
            "current_corp_index": self._current_corp_index,
        }

    def trigger_now(self) -> dict:
        """Trigger an immediate scan (skip to next run)."""
        if self._status != SchedulerStatus.RUNNING:
            return {
                "status": "error",
                "message": "Scheduler is not running"
            }

        # Run scan immediately in background
        result = self._run_scan()

        return {
            "status": "triggered",
            "result": result
        }

    def _load_corporations(self):
        """Load the list of corporations to scan."""
        try:
            with get_sync_db() as db:
                result = db.execute(text("""
                    SELECT corp_id, corp_name
                    FROM corp
                    ORDER BY corp_id
                """))
                self._corporations = [
                    {"corp_id": row[0], "corp_name": row[1]}
                    for row in result.fetchall()
                ]
                self._current_corp_index = 0
                logger.info(f"Loaded {len(self._corporations)} corporations for scanning")
        except Exception as e:
            logger.error(f"Failed to load corporations: {e}")
            self._corporations = []

    def _run_loop(self):
        """Main scheduler loop."""
        logger.info("Scheduler loop started")

        while not self._stop_event.is_set():
            try:
                # Calculate next run time
                self._next_run = datetime.now(UTC)

                # Run the scan
                self._run_scan()

                # Wait for next interval
                wait_seconds = self._interval_minutes * 60
                logger.info(f"Waiting {wait_seconds} seconds until next scan...")

                # Check stop event periodically during wait
                for _ in range(wait_seconds):
                    if self._stop_event.is_set():
                        break
                    time.sleep(1)

            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                time.sleep(10)  # Wait before retry

        logger.info("Scheduler loop ended")

    def _run_scan(self) -> dict:
        """Run a single scan cycle."""
        self._last_run = datetime.now(UTC)
        self._total_runs += 1

        logger.info(f"Starting scan cycle #{self._total_runs}")

        jobs_created = 0
        signals_before = self._get_total_signals()

        try:
            with get_sync_db() as db:
                # Scan all corporations (or round-robin one at a time for demo)
                for corp in self._corporations:
                    corp_id = corp["corp_id"]
                    corp_name = corp["corp_name"]

                    # Check for recent job
                    recent_job = db.execute(text("""
                        SELECT job_id FROM rkyc_job
                        WHERE corp_id = :corp_id
                          AND status IN ('QUEUED', 'RUNNING')
                        LIMIT 1
                    """), {"corp_id": corp_id}).fetchone()

                    if recent_job:
                        logger.debug(f"Skipping {corp_name} - job in progress")
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

                    # Queue analysis task
                    run_analysis_pipeline.delay(job_id, corp_id)
                    jobs_created += 1
                    logger.info(f"Queued analysis for {corp_name}")

            # Update signal count
            signals_after = self._get_total_signals()
            new_signals = signals_after - signals_before
            self._total_signals_detected += new_signals

            result = {
                "cycle": self._total_runs,
                "jobs_created": jobs_created,
                "corporations_scanned": len(self._corporations),
                "new_signals": new_signals,
                "timestamp": self._last_run.isoformat()
            }

            logger.info(f"Scan cycle #{self._total_runs} complete: {jobs_created} jobs, {new_signals} new signals")
            return result

        except Exception as e:
            logger.error(f"Scan cycle failed: {e}")
            return {
                "cycle": self._total_runs,
                "error": str(e),
                "timestamp": self._last_run.isoformat()
            }

    def _get_total_signals(self) -> int:
        """Get total signal count from database."""
        try:
            with get_sync_db() as db:
                result = db.execute(text("SELECT COUNT(*) FROM rkyc_signal"))
                return result.scalar() or 0
        except Exception:
            return 0


# Global scheduler instance
def get_scheduler() -> DynamicScheduler:
    """Get the singleton scheduler instance."""
    return DynamicScheduler()


# Celery task wrappers for API calls
@celery_app.task(name="start_dynamic_scheduler")
def start_dynamic_scheduler(interval_minutes: int = 5) -> dict:
    """Start the dynamic scheduler via Celery task."""
    scheduler = get_scheduler()
    return scheduler.start(interval_minutes)


@celery_app.task(name="stop_dynamic_scheduler")
def stop_dynamic_scheduler() -> dict:
    """Stop the dynamic scheduler via Celery task."""
    scheduler = get_scheduler()
    return scheduler.stop()
