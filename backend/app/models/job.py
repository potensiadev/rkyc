"""
rKYC Job Model
분석 작업 (PRD 14.9.1)
"""

from sqlalchemy import Column, String, Integer, Text, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class JobType(str, enum.Enum):
    ANALYZE = "ANALYZE"
    EXTERNAL_COLLECT = "EXTERNAL_COLLECT"


class JobStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"


class ProgressStep(str, enum.Enum):
    SNAPSHOT = "SNAPSHOT"
    DOC_INGEST = "DOC_INGEST"
    EXTERNAL = "EXTERNAL"
    UNIFIED_CONTEXT = "UNIFIED_CONTEXT"
    SIGNAL = "SIGNAL"
    INDEX = "INDEX"


class Job(Base):
    """분석 작업 모델 (rkyc_job 테이블)"""

    __tablename__ = "rkyc_job"

    job_id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    job_type = Column(
        SQLEnum(JobType, name="job_type_enum", create_type=False),
        nullable=False,
        default=JobType.ANALYZE,
    )
    corp_id = Column(String(20), nullable=True)
    status = Column(
        SQLEnum(JobStatus, name="job_status_enum", create_type=False),
        nullable=False,
        default=JobStatus.QUEUED,
    )
    progress_step = Column(
        SQLEnum(ProgressStep, name="progress_step_enum", create_type=False),
        nullable=True,
    )
    progress_percent = Column(Integer, default=0)
    error_code = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)
    queued_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
