"""
rKYC Signals API Endpoints
Query operations for signals (PRD 14.7.3)

Endpoints:
- GET    /signals                    - 시그널 목록 (필터링 지원)
- GET    /signals/{signal_id}        - 시그널 기본 조회
- GET    /signals/{signal_id}/detail - 시그널 상세 (Evidence 포함)
- PATCH  /signals/{signal_id}/status - 상태 변경
- POST   /signals/{signal_id}/dismiss - 기각

Migration v11 변경사항:
- rkyc_signal_index에서 상태 필드 제거됨 (immutable)
- 상태 조회는 rkyc_signal 테이블과 JOIN 필요
- 상태 업데이트는 rkyc_signal 테이블만 업데이트
"""

from typing import Optional
from uuid import UUID
from datetime import datetime, UTC
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from sqlalchemy.orm import selectinload
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
    시그널 목록 조회 (Dashboard용)

    Migration v11 변경:
    - 항상 Signal 테이블과 JOIN하여 상태 정보 조회
    - signal_index는 immutable, 상태는 signal에서만 관리
    """

    # 항상 JOIN으로 상태 정보 조회 (v11: signal_index에서 상태 필드 제거)
    query = (
        select(
            SignalIndex,
            Signal.signal_status,
            Signal.reviewed_at,
            Signal.dismissed_at,
            Signal.dismiss_reason
        )
        .join(Signal, Signal.signal_id == SignalIndex.signal_id)
    )

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

    # 상태 필터는 Signal 테이블에서 적용
    if signal_status:
        query = query.where(Signal.signal_status == signal_status)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Get items with pagination (sorted by detected_at DESC)
    query = query.limit(limit).offset(offset).order_by(SignalIndex.detected_at.desc())
    result = await db.execute(query)
    rows = result.all()

    # 결과 변환: SignalIndex + Signal 상태 정보 병합
    items = []
    for row in rows:
        signal_index = row[0]
        # SignalIndexResponse 형태로 변환
        items.append(SignalIndexResponse(
            index_id=signal_index.index_id,
            corp_id=signal_index.corp_id,
            corp_name=signal_index.corp_name,
            industry_code=signal_index.industry_code,
            signal_type=signal_index.signal_type,
            event_type=signal_index.event_type,
            impact_direction=signal_index.impact_direction,
            impact_strength=signal_index.impact_strength,
            confidence=signal_index.confidence,
            title=signal_index.title,
            summary_short=signal_index.summary_short,
            evidence_count=signal_index.evidence_count,
            detected_at=signal_index.detected_at,
            signal_id=signal_index.signal_id,
            # 상태 정보는 Signal 테이블에서 가져옴
            signal_status=row[1] or SignalStatusEnum.NEW,
            reviewed_at=row[2],
            dismissed_at=row[3],
            dismiss_reason=row[4],
        ))

    return SignalListResponse(total=total, items=items)


@router.get("/{signal_id}", response_model=SignalIndexResponse)
async def get_signal(
    signal_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    시그널 기본 조회

    Migration v11 변경:
    - Signal 테이블과 JOIN하여 상태 정보 조회
    """

    query = (
        select(
            SignalIndex,
            Signal.signal_status,
            Signal.reviewed_at,
            Signal.dismissed_at,
            Signal.dismiss_reason
        )
        .join(Signal, Signal.signal_id == SignalIndex.signal_id)
        .where(SignalIndex.signal_id == signal_id)
    )
    result = await db.execute(query)
    row = result.one_or_none()

    if not row:
        raise HTTPException(status_code=404, detail="Signal not found")

    signal_index = row[0]
    return SignalIndexResponse(
        index_id=signal_index.index_id,
        corp_id=signal_index.corp_id,
        corp_name=signal_index.corp_name,
        industry_code=signal_index.industry_code,
        signal_type=signal_index.signal_type,
        event_type=signal_index.event_type,
        impact_direction=signal_index.impact_direction,
        impact_strength=signal_index.impact_strength,
        confidence=signal_index.confidence,
        title=signal_index.title,
        summary_short=signal_index.summary_short,
        evidence_count=signal_index.evidence_count,
        detected_at=signal_index.detected_at,
        signal_id=signal_index.signal_id,
        signal_status=row[1] or SignalStatusEnum.NEW,
        reviewed_at=row[2],
        dismissed_at=row[3],
        dismiss_reason=row[4],
    )


@router.get("/{signal_id}/detail", response_model=SignalDetailResponse)
async def get_signal_detail(
    signal_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    시그널 상세 조회 (Evidence 포함)

    Migration v11 변경:
    - 상태 정보(signal_status, reviewed_at, dismissed_at, dismiss_reason)는
      Signal 테이블에서만 조회 (signal_index는 상태 필드 없음)

    N+1 최적화 (v11.1):
    - Query 1: SignalIndex + Signal JOIN (기존 3개 → 1개)
    - Query 2: Evidence 조회 (배열이므로 별도)
    """

    # Query 1: SignalIndex + Signal JOIN으로 한 번에 조회
    combined_query = (
        select(SignalIndex, Signal)
        .outerjoin(Signal, Signal.signal_id == SignalIndex.signal_id)
        .where(SignalIndex.signal_id == signal_id)
    )
    combined_result = await db.execute(combined_query)
    row = combined_result.one_or_none()

    if not row:
        raise HTTPException(status_code=404, detail="Signal not found")

    signal_index, signal = row

    # Query 2: Evidence 조회
    evidence_query = select(Evidence).where(Evidence.signal_id == signal_id).order_by(Evidence.created_at.desc())
    evidence_result = await db.execute(evidence_query)
    evidences = evidence_result.scalars().all()

    # 상태 정보는 Signal 테이블에서 가져옴 (v11: signal_index에서 제거됨)
    signal_status = signal.signal_status if signal else SignalStatusEnum.NEW
    reviewed_at = signal.reviewed_at if signal else None
    dismissed_at = signal.dismissed_at if signal else None
    dismiss_reason = signal.dismiss_reason if signal else None

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
        signal_status=signal_status,
        evidence_count=signal_index.evidence_count,
        detected_at=signal_index.detected_at,
        reviewed_at=reviewed_at,
        dismissed_at=dismissed_at,
        dismiss_reason=dismiss_reason,
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
    """
    시그널 상태 변경 (NEW → REVIEWED)

    Migration v11 변경:
    - rkyc_signal 테이블만 업데이트 (signal_index는 상태 필드 없음)
    - 일관성 문제 해결 (단일 소스)
    """

    now = datetime.now(UTC)
    status_value = status_update.status.value  # "NEW", "REVIEWED", "DISMISSED"

    # 시그널 존재 확인 (Signal 테이블에서 직접 확인)
    signal_query = select(Signal).where(Signal.signal_id == signal_id)
    signal_result = await db.execute(signal_query)
    signal = signal_result.scalar_one_or_none()

    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")

    params = {"status": status_value, "now": now, "signal_id": str(signal_id)}

    try:
        # rkyc_signal 테이블만 업데이트 (v11: signal_index 업데이트 제거)
        await db.execute(
            text("""
                UPDATE rkyc_signal
                SET signal_status = CAST(:status AS signal_status_enum),
                    reviewed_at = CASE WHEN :status = 'REVIEWED' THEN :now ELSE reviewed_at END,
                    last_updated_at = :now
                WHERE signal_id = CAST(:signal_id AS uuid)
            """),
            params
        )

        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update signal status: {str(e)[:200]}"
        )

    return {"message": "Status updated", "status": status_value}


@router.post("/{signal_id}/dismiss")
async def dismiss_signal(
    signal_id: UUID,
    dismiss_request: SignalDismissRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    시그널 기각 (사유 포함)

    Migration v11 변경:
    - rkyc_signal 테이블만 업데이트 (signal_index는 상태 필드 없음)
    - 일관성 문제 해결 (단일 소스)
    """

    now = datetime.now(UTC)

    # 시그널 존재 확인 (Signal 테이블에서 직접 확인)
    signal_query = select(Signal).where(Signal.signal_id == signal_id)
    signal_result = await db.execute(signal_query)
    signal = signal_result.scalar_one_or_none()

    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")

    params = {"now": now, "reason": dismiss_request.reason, "signal_id": str(signal_id)}

    try:
        # rkyc_signal 테이블만 업데이트 (v11: signal_index 업데이트 제거)
        await db.execute(
            text("""
                UPDATE rkyc_signal
                SET signal_status = CAST('DISMISSED' AS signal_status_enum),
                    dismissed_at = :now,
                    dismiss_reason = :reason,
                    last_updated_at = :now
                WHERE signal_id = CAST(:signal_id AS uuid)
            """),
            params
        )

        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to dismiss signal: {str(e)[:200]}"
        )

    return {"message": "Signal dismissed", "reason": dismiss_request.reason}
