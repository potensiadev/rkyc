"""
Internal Snapshot Models
PRD 14.2 - Internal Snapshot 버전 관리
"""

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class InternalSnapshot(Base):
    """Internal Snapshot 버전 관리 (PRD 14.2.1)"""
    __tablename__ = "rkyc_internal_snapshot"

    snapshot_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    corp_id = Column(String(20), ForeignKey("corp.corp_id"), nullable=False)
    snapshot_version = Column(Integer, nullable=False)
    snapshot_json = Column(JSONB, nullable=False)  # PRD 7장 스키마 준수
    snapshot_hash = Column(String(64), nullable=False)  # sha256
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class InternalSnapshotLatest(Base):
    """최신 Snapshot 포인터 (PRD 14.2.2)"""
    __tablename__ = "rkyc_internal_snapshot_latest"

    corp_id = Column(String(20), ForeignKey("corp.corp_id"), primary_key=True)
    snapshot_id = Column(UUID(as_uuid=True), ForeignKey("rkyc_internal_snapshot.snapshot_id"), nullable=False)
    snapshot_version = Column(Integer, nullable=False)
    snapshot_hash = Column(String(64), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now())
