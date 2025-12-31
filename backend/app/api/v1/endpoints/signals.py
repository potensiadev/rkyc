"""
rKYC Signals API Endpoints
Query operations for signals (PRD 14.7.3)

Endpoints:
- GET    /signals                    - 시그널 목록 (필터링 지원)
- GET    /signals/{signal_id}        - 시그널 기본 조회
- GET    /signals/{signal_id}/detail - 시그널 상세 (Evidence 포함)
- PATCH  /signals/{signal_id}/status - 상태 변경
- POST   /signals/{signal_id}/dismiss - 기각
"""

from typing import Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from app.core.database import get_db
from app.models.signal import (
    SignalIndex,
    Signal,
    Evidence,
    SignalType,
    EventType,
    ImpactDirection,
    ImpactStrength,
    SignalStatus,
)
from app.schemas.signal import (
    SignalIndexResponse,
    SignalListResponse,
    SignalDetailResponse,
    SignalStatusUpdate,
    SignalDismissRequest,
    EvidenceResponse,
    SignalStatusEnum,
)

router = APIRouter()


@router.get("", response_model=SignalListResponse)
async def list_signals(
    signal_type: Optional[SignalType] = Query(None, description="시그널 타입 필터"),
    event_type: Optional[EventType] = Query(None, description="이벤트 타입 필터"),
    impact_direction: Optional[ImpactDirection] = Query(None, description="영향 방향 필터"),
    impact_strength: Optional[ImpactStrength] = Query(None, description="영향 강도 필터"),
    signal_status: Optional[SignalStatus] = Query(None, description="시그널 상태 필터"),
    corp_id: Optional[str] = Query(None, description="기업 ID 필터"),
    industry_code: Optional[str] = Query(None, description="업종코드 필터"),
    limit: int = Query(50, ge=1, le=1000),
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

    if signal_status:
        query = query.where(SignalIndex.signal_status == signal_status)

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
    """시그널 기본 조회"""

    query = select(SignalIndex).where(SignalIndex.signal_id == signal_id)
    result = await db.execute(query)
    signal = result.scalar_one_or_none()

    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")

    return signal


@router.get("/{signal_id}/detail", response_model=SignalDetailResponse)
async def get_signal_detail(
    signal_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """시그널 상세 조회 (Evidence 포함)"""

    # SignalIndex에서 기본 정보
    index_query = select(SignalIndex).where(SignalIndex.signal_id == signal_id)
    index_result = await db.execute(index_query)
    signal_index = index_result.scalar_one_or_none()

    if not signal_index:
        raise HTTPException(status_code=404, detail="Signal not found")

    # Signal 원본에서 전체 summary
    signal_query = select(Signal).where(Signal.signal_id == signal_id)
    signal_result = await db.execute(signal_query)
    signal = signal_result.scalar_one_or_none()

    # Evidence 조회
    evidence_query = select(Evidence).where(Evidence.signal_id == signal_id)
    evidence_result = await db.execute(evidence_query)
    evidences = evidence_result.scalars().all()

    return SignalDetailResponse(
        signal_id=signal_index.signal_id,
        corp_id=signal_index.corp_id,
        corp_name=signal_index.corp_name,
        industry_code=signal_index.industry_code,
        signal_type=signal_index.signal_type,
        event_type=signal_index.event_type,
        impact_direction=signal_index.impact_direction,
        impact_strength=signal_index.impact_strength,
        confidence=signal_index.confidence,
        title=signal_index.title,
        summary=signal.summary if signal else signal_index.summary_short or "",
        summary_short=signal_index.summary_short,
        signal_status=signal_index.signal_status or SignalStatusEnum.NEW,
        evidence_count=signal_index.evidence_count,
        detected_at=signal_index.detected_at,
        reviewed_at=signal_index.reviewed_at,
        dismissed_at=signal_index.dismissed_at,
        dismiss_reason=signal_index.dismiss_reason,
        evidences=[
            EvidenceResponse(
                evidence_id=e.evidence_id,
                signal_id=e.signal_id,
                evidence_type=e.evidence_type,
                ref_type=e.ref_type,
                ref_value=e.ref_value,
                snippet=e.snippet,
                meta=e.meta,
                created_at=e.created_at,
            )
            for e in evidences
        ],
    )


@router.patch("/{signal_id}/status")
async def update_signal_status(
    signal_id: UUID,
    status_update: SignalStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    """시그널 상태 변경 (NEW → REVIEWED)"""

    now = datetime.utcnow()
    status_value = status_update.status.value  # "NEW", "REVIEWED", "DISMISSED"

    # rkyc_signal_index 업데이트 (Dashboard용)
    index_query = select(SignalIndex).where(SignalIndex.signal_id == signal_id)
    index_result = await db.execute(index_query)
    signal_index = index_result.scalar_one_or_none()

    if not signal_index:
        raise HTTPException(status_code=404, detail="Signal not found")

    # Raw SQL로 업데이트 (CAST 함수 사용)
    await db.execute(
        text("""
            UPDATE rkyc_signal_index
            SET signal_status = CAST(:status AS signal_status_enum),
                reviewed_at = CASE WHEN :status = 'REVIEWED' THEN :now ELSE reviewed_at END,
                last_updated_at = :now
            WHERE signal_id = CAST(:signal_id AS uuid)
        """),
        {"status": status_value, "now": now, "signal_id": str(signal_id)}
    )

    await db.commit()

    return {"message": "Status updated", "status": status_value}


@router.post("/{signal_id}/dismiss")
async def dismiss_signal(
    signal_id: UUID,
    dismiss_request: SignalDismissRequest,
    db: AsyncSession = Depends(get_db),
):
    """시그널 기각 (사유 포함)"""

    now = datetime.utcnow()

    # 시그널 존재 확인
    index_query = select(SignalIndex).where(SignalIndex.signal_id == signal_id)
    index_result = await db.execute(index_query)
    signal_index = index_result.scalar_one_or_none()

    if not signal_index:
        raise HTTPException(status_code=404, detail="Signal not found")

    # Raw SQL로 업데이트 (CAST 함수 사용)
    await db.execute(
        text("""
            UPDATE rkyc_signal_index
            SET signal_status = CAST('DISMISSED' AS signal_status_enum),
                dismissed_at = :now,
                dismiss_reason = :reason,
                last_updated_at = :now
            WHERE signal_id = CAST(:signal_id AS uuid)
        """),
        {"now": now, "reason": dismiss_request.reason, "signal_id": str(signal_id)}
    )

    await db.commit()

    return {"message": "Signal dismissed", "reason": dismiss_request.reason}
