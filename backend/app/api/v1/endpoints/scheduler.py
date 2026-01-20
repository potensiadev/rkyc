"""
Scheduler Control API Endpoints
Real-time control of automated signal detection for demo purposes
"""

from enum import Enum
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.worker.tasks.dynamic_scheduler import get_scheduler, SchedulerStatus

router = APIRouter()


# =============================================================================
# Schemas
# =============================================================================

class IntervalEnum(int, Enum):
    ONE_MINUTE = 1
    THREE_MINUTES = 3
    FIVE_MINUTES = 5
    TEN_MINUTES = 10


class SchedulerStartRequest(BaseModel):
    interval_minutes: IntervalEnum = Field(
        default=IntervalEnum.FIVE_MINUTES,
        description="Scan interval in minutes (1, 3, 5, or 10)"
    )


class SchedulerIntervalRequest(BaseModel):
    interval_minutes: IntervalEnum = Field(
        ...,
        description="New scan interval in minutes"
    )


class SchedulerStatusResponse(BaseModel):
    status: str = Field(..., description="Current scheduler status (STOPPED, RUNNING, PAUSED)")
    interval_minutes: int = Field(..., description="Current scan interval in minutes")
    last_run: Optional[str] = Field(None, description="Last scan timestamp (ISO format)")
    next_run: Optional[str] = Field(None, description="Next scheduled scan timestamp")
    total_runs: int = Field(..., description="Total number of scan cycles completed")
    total_signals_detected: int = Field(..., description="Total new signals detected")
    corporations_count: int = Field(..., description="Number of corporations being monitored")
    current_corp_index: int = Field(0, description="Current corporation index in round-robin")


class SchedulerActionResponse(BaseModel):
    status: str = Field(..., description="Action result status")
    message: str = Field(..., description="Human-readable message")
    interval_minutes: Optional[int] = Field(None, description="Current/new interval")
    corporations_count: Optional[int] = Field(None, description="Number of corporations")


# =============================================================================
# Endpoints
# =============================================================================

@router.get(
    "/status",
    response_model=SchedulerStatusResponse,
    summary="Get scheduler status",
    description="Get the current status of the real-time signal detection scheduler"
)
async def get_scheduler_status():
    """
    Get current scheduler status including:
    - Running state (STOPPED, RUNNING, PAUSED)
    - Current interval setting
    - Last/next run times
    - Statistics (total runs, signals detected)
    """
    scheduler = get_scheduler()
    status_data = scheduler.get_status()

    return SchedulerStatusResponse(
        status=status_data["status"],
        interval_minutes=status_data["interval_minutes"],
        last_run=status_data["last_run"],
        next_run=status_data["next_run"],
        total_runs=status_data["total_runs"],
        total_signals_detected=status_data["total_signals_detected"],
        corporations_count=status_data["corporations_count"],
        current_corp_index=status_data["current_corp_index"],
    )


@router.post(
    "/start",
    response_model=SchedulerActionResponse,
    summary="Start the scheduler",
    description="Start real-time signal detection with specified interval"
)
async def start_scheduler(request: SchedulerStartRequest):
    """
    Start the real-time signal detection scheduler.

    - **interval_minutes**: Scan interval (1, 3, 5, or 10 minutes)

    The scheduler will:
    1. Load all corporations from the database
    2. Periodically scan each corporation for new signals
    3. Queue analysis jobs for each corporation
    """
    scheduler = get_scheduler()
    result = scheduler.start(request.interval_minutes.value)

    return SchedulerActionResponse(
        status=result["status"],
        message=result.get("message", ""),
        interval_minutes=result.get("interval_minutes"),
        corporations_count=result.get("corporations_count"),
    )


@router.post(
    "/stop",
    response_model=SchedulerActionResponse,
    summary="Stop the scheduler",
    description="Stop real-time signal detection"
)
async def stop_scheduler():
    """
    Stop the real-time signal detection scheduler.

    All pending jobs will complete, but no new scans will be triggered.
    """
    scheduler = get_scheduler()
    result = scheduler.stop()

    return SchedulerActionResponse(
        status=result["status"],
        message=result.get("message", ""),
    )


@router.patch(
    "/interval",
    response_model=SchedulerActionResponse,
    summary="Change scan interval",
    description="Change the scan interval while scheduler is running"
)
async def set_scheduler_interval(request: SchedulerIntervalRequest):
    """
    Change the scan interval without stopping the scheduler.

    - **interval_minutes**: New interval (1, 3, 5, or 10 minutes)

    The new interval takes effect from the next scan cycle.
    """
    scheduler = get_scheduler()
    result = scheduler.set_interval(request.interval_minutes.value)

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])

    return SchedulerActionResponse(
        status=result["status"],
        message=result.get("message", ""),
        interval_minutes=result.get("new_interval"),
    )


@router.post(
    "/trigger",
    response_model=dict,
    summary="Trigger immediate scan",
    description="Trigger an immediate scan without waiting for the next scheduled time"
)
async def trigger_immediate_scan():
    """
    Trigger an immediate scan cycle.

    This is useful for demo purposes to see results without waiting.
    The scheduler must be running for this to work.
    """
    scheduler = get_scheduler()

    if scheduler.status != SchedulerStatus.RUNNING:
        raise HTTPException(
            status_code=400,
            detail="Scheduler is not running. Start it first."
        )

    result = scheduler.trigger_now()

    return result
