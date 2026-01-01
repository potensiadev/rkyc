"""
rKYC Dashboard API Endpoints
Dashboard 통계 조회

Endpoints:
- GET /dashboard/summary - Dashboard 요약 통계
"""

from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, literal_column
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
    """
    Dashboard 요약 통계

    최적화: 단일 쿼리로 모든 통계를 집계 (N+1 문제 해결)
    """

    # 단일 쿼리로 모든 통계 집계
    stats_query = select(
        func.count().label("total"),
        # Impact Direction 카운트
        func.sum(case((SignalIndex.impact_direction == ImpactDirection.RISK, 1), else_=0)).label("risk"),
        func.sum(case((SignalIndex.impact_direction == ImpactDirection.OPPORTUNITY, 1), else_=0)).label("opportunity"),
        func.sum(case((SignalIndex.impact_direction == ImpactDirection.NEUTRAL, 1), else_=0)).label("neutral"),
        # Signal Type 카운트
        func.sum(case((SignalIndex.signal_type == SignalType.DIRECT, 1), else_=0)).label("type_direct"),
        func.sum(case((SignalIndex.signal_type == SignalType.INDUSTRY, 1), else_=0)).label("type_industry"),
        func.sum(case((SignalIndex.signal_type == SignalType.ENVIRONMENT, 1), else_=0)).label("type_environment"),
        # Signal Status 카운트 (NULL은 NEW로 집계)
        func.sum(case(
            (SignalIndex.signal_status == SignalStatus.NEW, 1),
            (SignalIndex.signal_status.is_(None), 1),
            else_=0
        )).label("status_new"),
        func.sum(case((SignalIndex.signal_status == SignalStatus.REVIEWED, 1), else_=0)).label("status_reviewed"),
        func.sum(case((SignalIndex.signal_status == SignalStatus.DISMISSED, 1), else_=0)).label("status_dismissed"),
    ).select_from(SignalIndex)

    result = await db.execute(stats_query)
    row = result.one()

    # 결과 구성
    type_counts = {
        SignalType.DIRECT.value: row.type_direct or 0,
        SignalType.INDUSTRY.value: row.type_industry or 0,
        SignalType.ENVIRONMENT.value: row.type_environment or 0,
    }

    status_counts = {
        SignalStatus.NEW.value: row.status_new or 0,
        SignalStatus.REVIEWED.value: row.status_reviewed or 0,
        SignalStatus.DISMISSED.value: row.status_dismissed or 0,
    }

    return DashboardSummaryResponse(
        total_signals=row.total or 0,
        new_signals=row.status_new or 0,
        risk_signals=row.risk or 0,
        opportunity_signals=row.opportunity or 0,
        by_type=type_counts,
        by_status=status_counts,
        generated_at=datetime.utcnow(),
    )
