"""
rKYC Signal Schemas
Pydantic models for signal request/response (PRD 14.7)
"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field
from app.models.signal import (
    SignalType,
    EventType,
    ImpactDirection,
    ImpactStrength,
    ConfidenceLevel,
)


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
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
