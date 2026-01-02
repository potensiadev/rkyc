"""
rKYC Jobs API Endpoints
분석 작업 트리거 및 상태 조회 (Demo Mode)
"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional

from app.core.database import get_db
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
        print(f"Celery task dispatched: task_id={task.id}, job_id={new_job.job_id}")
    except Exception as e:
        # Redis 연결 실패 등의 경우
        celery_dispatch_failed = True
        celery_error_message = str(e)
        print(f"Celery task dispatch failed: {e}")

        # Job 상태를 FAILED로 업데이트하여 사용자에게 알림
        new_job.status = JobStatus.FAILED
        new_job.error_code = "CELERY_DISPATCH_FAILED"
        new_job.error_message = f"Worker 연결 실패: {str(e)[:200]}"
        await db.commit()
        await db.refresh(new_job)

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
