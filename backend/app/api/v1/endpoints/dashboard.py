"""
rKYC Dashboard API Endpoints
Dashboard 통계 조회

Endpoints:
- GET /dashboard/summary - Dashboard 요약 통계
"""

from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.models.signal import (
    SignalIndex,
    SignalType,
    ImpactDirection,
    SignalStatus,
)
from app.schemas.signal import DashboardSummaryResponse

router = APIRouter()


@router.get("/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(db: AsyncSession = Depends(get_db)):
    """Dashboard 요약 통계"""

    # 전체 카운트
    total_query = select(func.count()).select_from(SignalIndex)
    total = (await db.execute(total_query)).scalar_one()

    # NEW 상태 카운트 (NULL도 NEW로 취급)
    new_query = select(func.count()).select_from(SignalIndex).where(
        (SignalIndex.signal_status == SignalStatus.NEW)
        | (SignalIndex.signal_status.is_(None))
    )
    new_count = (await db.execute(new_query)).scalar_one() or 0

    # RISK 카운트
    risk_query = (
        select(func.count())
        .select_from(SignalIndex)
        .where(SignalIndex.impact_direction == ImpactDirection.RISK)
    )
    risk_count = (await db.execute(risk_query)).scalar_one()

    # OPPORTUNITY 카운트
    opp_query = (
        select(func.count())
        .select_from(SignalIndex)
        .where(SignalIndex.impact_direction == ImpactDirection.OPPORTUNITY)
    )
    opp_count = (await db.execute(opp_query)).scalar_one()

    # Signal Type별 카운트
    type_counts = {}
    for signal_type in SignalType:
        type_query = (
            select(func.count())
            .select_from(SignalIndex)
            .where(SignalIndex.signal_type == signal_type)
        )
        type_counts[signal_type.value] = (await db.execute(type_query)).scalar_one()

    # Status별 카운트 (NULL은 NEW로 집계)
    status_counts = {}
    for status in SignalStatus:
        if status == SignalStatus.NEW:
            # NEW와 NULL 모두 집계
            status_query = (
                select(func.count())
                .select_from(SignalIndex)
                .where(
                    (SignalIndex.signal_status == status)
                    | (SignalIndex.signal_status.is_(None))
                )
            )
        else:
            status_query = (
                select(func.count())
                .select_from(SignalIndex)
                .where(SignalIndex.signal_status == status)
            )
        status_counts[status.value] = (await db.execute(status_query)).scalar_one()

    return DashboardSummaryResponse(
        total_signals=total,
        new_signals=new_count,
        risk_signals=risk_count,
        opportunity_signals=opp_count,
        by_type=type_counts,
        by_status=status_counts,
        generated_at=datetime.utcnow(),
    )
