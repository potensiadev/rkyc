"""
rKYC Signals API Endpoints
Query operations for signals (PRD 14.7.3)

Endpoints:
- GET    /signals                - 시그널 목록 (필터링 지원)
- GET    /signals/{signal_id}    - 시그널 상세
"""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.models.signal import (
    SignalIndex,
    SignalType,
    EventType,
    ImpactDirection,
    ImpactStrength,
)
from app.schemas.signal import SignalIndexResponse, SignalListResponse

router = APIRouter()


@router.get("", response_model=SignalListResponse)
async def list_signals(
    signal_type: Optional[SignalType] = Query(None, description="시그널 타입 필터"),
    event_type: Optional[EventType] = Query(None, description="이벤트 타입 필터"),
    impact_direction: Optional[ImpactDirection] = Query(None, description="영향 방향 필터"),
    impact_strength: Optional[ImpactStrength] = Query(None, description="영향 강도 필터"),
    corp_id: Optional[str] = Query(None, description="기업 ID 필터"),
    industry_code: Optional[str] = Query(None, description="업종코드 필터"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    시그널 목록 조회 (Dashboard용 - rkyc_signal_index 사용)

    IMPORTANT: 조인 금지! rkyc_signal_index는 denormalized 테이블
    """

    # Build query
    query = select(SignalIndex)

    # Apply filters
    if signal_type:
        query = query.where(SignalIndex.signal_type == signal_type)

    if event_type:
        query = query.where(SignalIndex.event_type == event_type)

    if impact_direction:
        query = query.where(SignalIndex.impact_direction == impact_direction)

    if impact_strength:
        query = query.where(SignalIndex.impact_strength == impact_strength)

    if corp_id:
        query = query.where(SignalIndex.corp_id == corp_id)

    if industry_code:
        query = query.where(SignalIndex.industry_code == industry_code)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Get items with pagination (sorted by detected_at DESC)
    query = query.limit(limit).offset(offset).order_by(SignalIndex.detected_at.desc())
    result = await db.execute(query)
    items = result.scalars().all()

    return SignalListResponse(total=total, items=items)


@router.get("/{signal_id}", response_model=SignalIndexResponse)
async def get_signal(
    signal_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """시그널 상세 조회"""

    query = select(SignalIndex).where(SignalIndex.signal_id == signal_id)
    result = await db.execute(query)
    signal = result.scalar_one_or_none()

    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")

    return signal
