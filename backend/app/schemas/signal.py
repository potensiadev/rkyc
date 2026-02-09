"""
rKYC Signal Schemas
Pydantic models for signal request/response (PRD 14.7)
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field
from enum import Enum
from app.models.signal import (
    SignalType,
    EventType,
    ImpactDirection,
    ImpactStrength,
    ConfidenceLevel,
)


# Signal Status Enum for API
class SignalStatusEnum(str, Enum):
    NEW = "NEW"
    REVIEWED = "REVIEWED"
    DISMISSED = "DISMISSED"


class SignalIndexResponse(BaseModel):
    """
    Signal Index response (Dashboard용)
    PRD 14.7.3 - rkyc_signal_index
    """

    index_id: UUID
    corp_id: str
    corp_name: str
    industry_code: str
    signal_type: SignalType
    event_type: EventType
    impact_direction: ImpactDirection
    impact_strength: ImpactStrength
    confidence: ConfidenceLevel
    title: str
    summary_short: Optional[str] = None
    evidence_count: int
    detected_at: datetime
    signal_id: UUID
    # Status fields (Session 5)
    signal_status: Optional[SignalStatusEnum] = SignalStatusEnum.NEW
    reviewed_at: Optional[datetime] = None
    dismissed_at: Optional[datetime] = None
    dismiss_reason: Optional[str] = None

    class Config:
        from_attributes = True


class SignalListResponse(BaseModel):
    """List of signals with pagination"""

    total: int
    items: list[SignalIndexResponse]


class SignalFilterParams(BaseModel):
    """Query parameters for filtering signals"""

    signal_type: Optional[SignalType] = None
    event_type: Optional[EventType] = None
    impact_direction: Optional[ImpactDirection] = None
    impact_strength: Optional[ImpactStrength] = None
    corp_id: Optional[str] = None
    industry_code: Optional[str] = None
    signal_status: Optional[SignalStatusEnum] = None
    limit: int = Field(default=50, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


# ============================================================
# Session 5: 상태 관리 및 상세 조회 스키마
# ============================================================


class SignalStatusUpdate(BaseModel):
    """Signal 상태 변경 요청"""

    status: SignalStatusEnum


class SignalDismissRequest(BaseModel):
    """Signal 기각 요청"""

    reason: str = Field(..., min_length=1, max_length=500)


class EvidenceResponse(BaseModel):
    """Evidence 응답"""

    evidence_id: UUID
    signal_id: UUID
    evidence_type: str  # INTERNAL_FIELD, DOC, EXTERNAL
    ref_type: str  # SNAPSHOT_KEYPATH, DOC_PAGE, URL
    ref_value: str
    snippet: Optional[str] = None
    meta: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SignalDetailResponse(BaseModel):
    """Signal 상세 응답 (Evidence 포함)"""

    signal_id: UUID
    corp_id: str
    corp_name: str
    industry_code: str
    signal_type: SignalType
    event_type: EventType
    impact_direction: ImpactDirection
    impact_strength: ImpactStrength
    confidence: ConfidenceLevel
    title: str
    summary: str  # 전체 요약 (rkyc_signal.summary)
    summary_short: Optional[str] = None
    signal_status: SignalStatusEnum
    evidence_count: int
    detected_at: datetime
    reviewed_at: Optional[datetime] = None
    dismissed_at: Optional[datetime] = None
    dismiss_reason: Optional[str] = None
    evidences: List[EvidenceResponse] = []
    # 은행 관점 재해석 (MVP)
    bank_interpretation: Optional[str] = None
    portfolio_impact: Optional[str] = None  # HIGH/MED/LOW
    recommended_action: Optional[str] = None
    action_priority: Optional[str] = None  # URGENT/NORMAL/LOW

    class Config:
        from_attributes = True


class DashboardSummaryResponse(BaseModel):
    """Dashboard 요약 통계"""

    total_signals: int
    new_signals: int
    risk_signals: int
    opportunity_signals: int
    by_type: dict  # {"DIRECT": 17, "INDUSTRY": 7, "ENVIRONMENT": 5}
    by_status: dict  # {"NEW": 25, "REVIEWED": 3, "DISMISSED": 1}
    generated_at: datetime
