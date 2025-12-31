"""
rKYC Job Schemas
분석 작업 Pydantic 스키마
"""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from typing import Optional

from app.models.job import JobType, JobStatus, ProgressStep


# Request Schemas
class JobTriggerRequest(BaseModel):
    """분석 작업 트리거 요청"""

    corp_id: str = Field(..., description="분석 대상 기업 ID")


# Response Schemas
class JobProgress(BaseModel):
    """작업 진행 상황"""

    step: Optional[str] = Field(None, description="현재 단계")
    percent: int = Field(0, description="진행률 (0-100)")


class JobError(BaseModel):
    """작업 오류 정보"""

    code: Optional[str] = Field(None, description="오류 코드")
    message: Optional[str] = Field(None, description="오류 메시지")


class JobTriggerResponse(BaseModel):
    """분석 작업 트리거 응답"""

    job_id: str = Field(..., description="생성된 작업 ID")
    status: str = Field(..., description="작업 상태")
    message: str = Field(..., description="응답 메시지")


class JobStatusResponse(BaseModel):
    """작업 상태 조회 응답"""

    job_id: str
    job_type: str
    corp_id: Optional[str]
    status: str
    progress: JobProgress
    error: Optional[JobError] = None
    queued_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    """작업 목록 응답"""

    total: int
    items: list[JobStatusResponse]
