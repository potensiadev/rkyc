"""
rKYC Jobs API Endpoints
분석 작업 트리거 및 상태 조회 (Demo Mode)
"""

import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional

from app.core.database import get_db

logger = logging.getLogger(__name__)
from app.models.job import Job, JobType, JobStatus
from app.models.corporation import Corporation
from app.schemas.job import (
    JobTriggerRequest,
    JobTriggerResponse,
    JobStatusResponse,
    JobListResponse,
    JobProgress,
    JobError,
)

router = APIRouter()


def job_to_response(job: Job) -> JobStatusResponse:
    """Job 모델을 응답 스키마로 변환"""
    return JobStatusResponse(
        job_id=str(job.job_id),
        job_type=job.job_type.value if job.job_type else "ANALYZE",
        corp_id=job.corp_id,
        status=job.status.value if job.status else "QUEUED",
        progress=JobProgress(
            step=job.progress_step.value if job.progress_step else None,
            percent=job.progress_percent or 0,
        ),
        error=JobError(code=job.error_code, message=job.error_message)
        if job.error_code or job.error_message
        else None,
        queued_at=job.queued_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )


@router.post("/analyze/run", response_model=JobTriggerResponse)
async def trigger_analyze_job(
    request: JobTriggerRequest,
    db: AsyncSession = Depends(get_db),
    x_demo_token: Optional[str] = Header(None, alias="X-DEMO-TOKEN"),
):
    """
    분석 작업 트리거 (Demo Mode)

    - Worker가 구현되면 실제 Celery 태스크를 큐에 등록
    - 현재는 Job 레코드만 생성 (QUEUED 상태)
    """
    # Demo 토큰 검증 (선택적 - 현재는 로깅만)
    # if x_demo_token:
    #     print(f"Demo token received: {x_demo_token[:8]}...")

    # 기업 존재 확인
    corp_query = select(Corporation).where(Corporation.corp_id == request.corp_id)
    corp_result = await db.execute(corp_query)
    if not corp_result.scalar_one_or_none():
        raise HTTPException(
            status_code=404,
            detail=f"Corporation not found: {request.corp_id}"
        )

    # Job 생성
    new_job = Job(
        job_type=JobType.ANALYZE,
        corp_id=request.corp_id,
        status=JobStatus.QUEUED,
    )

    db.add(new_job)
    await db.commit()
    await db.refresh(new_job)

    # Celery 태스크 호출
    celery_dispatch_failed = False
    celery_error_message = None
    try:
        from app.worker.tasks.analysis import run_analysis_pipeline
        task = run_analysis_pipeline.delay(str(new_job.job_id), request.corp_id)
        # Task ID는 로깅용 (Celery 결과 추적에 사용)
        logger.info(f"Celery task dispatched: task_id={task.id}, job_id={new_job.job_id}")
    except Exception as e:
        # Redis 연결 실패 등의 경우
        celery_dispatch_failed = True
        celery_error_message = str(e)
        logger.error(f"Celery task dispatch failed: {e}")

        # Job 상태를 FAILED로 업데이트하여 사용자에게 알림
        try:
            new_job.status = JobStatus.FAILED
            new_job.error_code = "CELERY_DISPATCH_FAILED"
            new_job.error_message = f"Worker 연결 실패: {str(e)[:200]}"
            await db.commit()
            await db.refresh(new_job)
        except Exception as commit_error:
            # 커밋도 실패한 경우 롤백 시도
            logger.error(f"Failed to update job status after Celery failure: {commit_error}")
            try:
                await db.rollback()
            except Exception:
                pass  # 롤백도 실패하면 무시

    if celery_dispatch_failed:
        return JobTriggerResponse(
            job_id=str(new_job.job_id),
            status=new_job.status.value,
            message=f"Worker 연결에 실패했습니다. 관리자에게 문의하세요. (오류: {celery_error_message[:100]})",
        )

    return JobTriggerResponse(
        job_id=str(new_job.job_id),
        status=new_job.status.value,
        message=f"분석 작업이 대기열에 등록되었습니다. (corp_id: {request.corp_id})",
    )


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """작업 상태 조회"""
    result = await db.execute(select(Job).where(Job.job_id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return job_to_response(job)


@router.get("", response_model=JobListResponse)
async def list_jobs(
    corp_id: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """작업 목록 조회"""
    query = select(Job)

    if corp_id:
        query = query.where(Job.corp_id == corp_id)
    if status:
        try:
            status_enum = JobStatus(status)
            query = query.where(Job.status == status_enum)
        except ValueError:
            pass  # 잘못된 status 값은 무시

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Fetch
    query = query.order_by(Job.queued_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    jobs = result.scalars().all()

    return JobListResponse(
        total=total,
        items=[job_to_response(job) for job in jobs],
    )


@router.get("/diagnostics/{corp_id}")
async def get_pipeline_diagnostics(
    corp_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    파이프라인 진단 API - 디버깅용

    corp_id에 대한 모든 관련 데이터 상태를 확인합니다:
    - 최근 Job 상태
    - Corp Profile 존재 여부
    - Signal Index 개수
    """
    from sqlalchemy import text

    diagnostics = {
        "corp_id": corp_id,
        "corporation": None,
        "recent_jobs": [],
        "profile": None,
        "signal_count": 0,
    }

    # 1. Corporation 존재 확인
    corp_result = await db.execute(
        text("SELECT corp_id, corp_name, industry_code FROM corp WHERE corp_id = :corp_id"),
        {"corp_id": corp_id}
    )
    corp_row = corp_result.fetchone()
    if corp_row:
        diagnostics["corporation"] = {
            "corp_id": corp_row.corp_id,
            "corp_name": corp_row.corp_name,
            "industry_code": corp_row.industry_code,
        }

    # 2. 최근 Jobs 조회 (최근 5개)
    jobs_result = await db.execute(
        text("""
            SELECT job_id, job_type, status, progress_step, progress_percent,
                   error_code, error_message, queued_at, started_at, finished_at
            FROM rkyc_job
            WHERE corp_id = :corp_id
            ORDER BY queued_at DESC
            LIMIT 5
        """),
        {"corp_id": corp_id}
    )
    for job_row in jobs_result.fetchall():
        diagnostics["recent_jobs"].append({
            "job_id": str(job_row.job_id),
            "job_type": job_row.job_type,
            "status": job_row.status,
            "progress_step": job_row.progress_step,
            "progress_percent": job_row.progress_percent,
            "error_code": job_row.error_code,
            "error_message": job_row.error_message,
            "queued_at": str(job_row.queued_at) if job_row.queued_at else None,
            "started_at": str(job_row.started_at) if job_row.started_at else None,
            "finished_at": str(job_row.finished_at) if job_row.finished_at else None,
        })

    # 3. Profile 존재 확인
    profile_result = await db.execute(
        text("""
            SELECT profile_id, corp_id, business_summary, profile_confidence,
                   is_fallback, search_failed, fetched_at, expires_at
            FROM rkyc_corp_profile
            WHERE corp_id = :corp_id
            LIMIT 1
        """),
        {"corp_id": corp_id}
    )
    profile_row = profile_result.fetchone()
    if profile_row:
        diagnostics["profile"] = {
            "profile_id": str(profile_row.profile_id),
            "corp_id": profile_row.corp_id,
            "has_business_summary": bool(profile_row.business_summary),
            "business_summary_preview": (profile_row.business_summary[:100] + "...") if profile_row.business_summary and len(profile_row.business_summary) > 100 else profile_row.business_summary,
            "profile_confidence": profile_row.profile_confidence,
            "is_fallback": profile_row.is_fallback,
            "search_failed": profile_row.search_failed,
            "fetched_at": str(profile_row.fetched_at) if profile_row.fetched_at else None,
            "expires_at": str(profile_row.expires_at) if profile_row.expires_at else None,
        }

    # 4. Signal 개수 확인
    signal_result = await db.execute(
        text("SELECT COUNT(*) as cnt FROM rkyc_signal_index WHERE corp_id = :corp_id"),
        {"corp_id": corp_id}
    )
    signal_row = signal_result.fetchone()
    diagnostics["signal_count"] = signal_row.cnt if signal_row else 0

    return diagnostics
