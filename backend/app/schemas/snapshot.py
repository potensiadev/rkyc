"""
Internal Snapshot Schemas
PRD 14.2 - Internal Snapshot API 응답
"""

from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime
from uuid import UUID


class SnapshotResponse(BaseModel):
    """Snapshot 상세 응답"""
    snapshot_id: UUID
    corp_id: str
    snapshot_version: int
    snapshot_json: dict  # PRD 7장 스키마 JSON
    snapshot_hash: str
    created_at: datetime

    class Config:
        from_attributes = True


class SnapshotLatestResponse(BaseModel):
    """최신 Snapshot 포인터 응답"""
    corp_id: str
    snapshot_id: UUID
    snapshot_version: int
    snapshot_hash: str
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SnapshotSummary(BaseModel):
    """Snapshot 요약 (목록용)"""
    snapshot_id: UUID
    snapshot_version: int
    snapshot_hash: str
    created_at: datetime

    class Config:
        from_attributes = True
