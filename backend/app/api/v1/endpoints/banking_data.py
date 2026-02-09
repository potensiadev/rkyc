"""
Banking Data API Endpoints
PRD: Internal Banking Data Integration v1.1

은행 내부 거래 데이터 API
- 여신/수신/카드/담보/무역금융/재무제표 조회
- 리스크 알림 및 영업 기회 조회
"""

from typing import Optional, List
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, func

from app.core.database import get_db
from app.models.banking_data import BankingData
from app.models.corporation import Corporation
from app.schemas.banking_data import (
    BankingDataResponse,
    BankingDataSummary,
    RiskAlertListResponse,
    OpportunityListResponse,
    RiskAlert,
    BankingDataCreate,
    BankingDataUpdate,
)
from app.services.dart_api import get_financial_statements_by_name, get_corp_code

router = APIRouter()


@router.get("/{corp_id}", response_model=BankingDataResponse)
async def get_banking_data(
    corp_id: str,
    data_date: Optional[date] = Query(None, description="기준일 (미지정 시 최신)"),
    db: AsyncSession = Depends(get_db),
):
    """
    기업의 Banking Data 조회

    최신 데이터 또는 특정 기준일 데이터를 반환합니다.
    """
    if data_date:
        query = select(BankingData).where(
            BankingData.corp_id == corp_id,
            BankingData.data_date == data_date
        )
    else:
        # 최신 데이터
        query = (
            select(BankingData)
            .where(BankingData.corp_id == corp_id)
            .order_by(BankingData.data_date.desc())
            .limit(1)
        )

    result = await db.execute(query)
    banking_data = result.scalar_one_or_none()

    if not banking_data:
        raise HTTPException(
            status_code=404,
            detail=f"Banking data not found for corp_id: {corp_id}"
        )

    return banking_data


@router.get("/{corp_id}/history", response_model=List[BankingDataSummary])
async def get_banking_data_history(
    corp_id: str,
    limit: int = Query(12, ge=1, le=60, description="조회 개수"),
    db: AsyncSession = Depends(get_db),
):
    """
    기업의 Banking Data 이력 조회

    최근 N개월 데이터를 반환합니다.
    """
    query = (
        select(BankingData)
        .where(BankingData.corp_id == corp_id)
        .order_by(BankingData.data_date.desc())
        .limit(limit)
    )

    result = await db.execute(query)
    rows = result.scalars().all()

    summaries = []
    for row in rows:
        loan_exposure = row.loan_exposure or {}
        deposit_trend = row.deposit_trend or {}
        risk_alerts = row.risk_alerts or []
        opportunity_signals = row.opportunity_signals or []

        summaries.append(BankingDataSummary(
            corp_id=row.corp_id,
            data_date=row.data_date,
            total_exposure_krw=loan_exposure.get("total_exposure_krw"),
            deposit_balance=deposit_trend.get("current_balance"),
            risk_count=len(risk_alerts),
            opportunity_count=len(opportunity_signals),
        ))

    return summaries


@router.get("/{corp_id}/risk-alerts", response_model=RiskAlertListResponse)
async def get_risk_alerts(
    corp_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    기업의 리스크 알림 조회

    최신 Banking Data에서 리스크 알림을 추출합니다.
    """
    query = (
        select(BankingData)
        .where(BankingData.corp_id == corp_id)
        .order_by(BankingData.data_date.desc())
        .limit(1)
    )

    result = await db.execute(query)
    banking_data = result.scalar_one_or_none()

    if not banking_data:
        raise HTTPException(
            status_code=404,
            detail=f"Banking data not found for corp_id: {corp_id}"
        )

    risk_alerts = banking_data.risk_alerts or []

    # 심각도별 집계
    high_count = sum(1 for a in risk_alerts if a.get("severity") == "HIGH")
    med_count = sum(1 for a in risk_alerts if a.get("severity") == "MED")
    low_count = sum(1 for a in risk_alerts if a.get("severity") == "LOW")

    return RiskAlertListResponse(
        corp_id=corp_id,
        total=len(risk_alerts),
        high_count=high_count,
        med_count=med_count,
        low_count=low_count,
        alerts=[RiskAlert(**a) for a in risk_alerts],
    )


@router.get("/{corp_id}/opportunities", response_model=OpportunityListResponse)
async def get_opportunities(
    corp_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    기업의 영업 기회 조회

    최신 Banking Data에서 영업 기회를 추출합니다.
    """
    query = (
        select(BankingData)
        .where(BankingData.corp_id == corp_id)
        .order_by(BankingData.data_date.desc())
        .limit(1)
    )

    result = await db.execute(query)
    banking_data = result.scalar_one_or_none()

    if not banking_data:
        raise HTTPException(
            status_code=404,
            detail=f"Banking data not found for corp_id: {corp_id}"
        )

    opportunities = banking_data.opportunity_signals or []

    return OpportunityListResponse(
        corp_id=corp_id,
        total=len(opportunities),
        opportunities=opportunities,
    )


@router.get("/{corp_id}/loan-exposure")
async def get_loan_exposure(
    corp_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    여신 현황 조회
    """
    query = (
        select(BankingData.loan_exposure)
        .where(BankingData.corp_id == corp_id)
        .order_by(BankingData.data_date.desc())
        .limit(1)
    )

    result = await db.execute(query)
    loan_exposure = result.scalar_one_or_none()

    if loan_exposure is None:
        raise HTTPException(status_code=404, detail="Loan exposure data not found")

    return loan_exposure


@router.get("/{corp_id}/deposit-trend")
async def get_deposit_trend(
    corp_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    수신 추이 조회
    """
    query = (
        select(BankingData.deposit_trend)
        .where(BankingData.corp_id == corp_id)
        .order_by(BankingData.data_date.desc())
        .limit(1)
    )

    result = await db.execute(query)
    deposit_trend = result.scalar_one_or_none()

    if deposit_trend is None:
        raise HTTPException(status_code=404, detail="Deposit trend data not found")

    return deposit_trend


@router.get("/{corp_id}/card-usage")
async def get_card_usage(
    corp_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    법인카드 이용 현황 조회
    """
    query = (
        select(BankingData.card_usage)
        .where(BankingData.corp_id == corp_id)
        .order_by(BankingData.data_date.desc())
        .limit(1)
    )

    result = await db.execute(query)
    card_usage = result.scalar_one_or_none()

    if card_usage is None:
        raise HTTPException(status_code=404, detail="Card usage data not found")

    return card_usage


@router.get("/{corp_id}/collateral")
async def get_collateral_detail(
    corp_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    담보물 현황 조회
    """
    query = (
        select(BankingData.collateral_detail)
        .where(BankingData.corp_id == corp_id)
        .order_by(BankingData.data_date.desc())
        .limit(1)
    )

    result = await db.execute(query)
    collateral_detail = result.scalar_one_or_none()

    if collateral_detail is None:
        raise HTTPException(status_code=404, detail="Collateral data not found")

    return collateral_detail


@router.get("/{corp_id}/trade-finance")
async def get_trade_finance(
    corp_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    무역금융 현황 조회
    """
    query = (
        select(BankingData.trade_finance)
        .where(BankingData.corp_id == corp_id)
        .order_by(BankingData.data_date.desc())
        .limit(1)
    )

    result = await db.execute(query)
    trade_finance = result.scalar_one_or_none()

    if trade_finance is None:
        raise HTTPException(status_code=404, detail="Trade finance data not found")

    return trade_finance


@router.get("/{corp_id}/financial-statements")
async def get_financial_statements(
    corp_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    재무제표 조회 (DB 저장 데이터)
    """
    query = (
        select(BankingData.financial_statements)
        .where(BankingData.corp_id == corp_id)
        .order_by(BankingData.data_date.desc())
        .limit(1)
    )

    result = await db.execute(query)
    financial_statements = result.scalar_one_or_none()

    if financial_statements is None:
        raise HTTPException(status_code=404, detail="Financial statements not found")

    return financial_statements


@router.get("/{corp_id}/financial-statements/dart")
async def get_financial_statements_from_dart(
    corp_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    DART 실시간 재무제표 조회 (100% Fact)

    DART 전자공시에서 최근 3년 재무제표를 실시간으로 조회합니다.
    - 매출액, 영업이익, 당기순이익
    - 총자산, 총부채, 총자본
    - 부채비율 자동 계산
    """
    # Get corp_name from corporation table
    corp_query = select(Corporation).where(Corporation.corp_id == corp_id)
    result = await db.execute(corp_query)
    corporation = result.scalar_one_or_none()

    if not corporation:
        raise HTTPException(status_code=404, detail=f"Corporation not found: {corp_id}")

    # Fetch from DART API
    statements = await get_financial_statements_by_name(corporation.corp_name)

    if not statements:
        raise HTTPException(
            status_code=404,
            detail=f"DART 재무제표를 찾을 수 없습니다: {corporation.corp_name}"
        )

    # Convert to dict format
    return {
        "corp_id": corp_id,
        "corp_name": corporation.corp_name,
        "source": "DART",
        "years": {s.bsns_year: s.to_dict() for s in statements},
        "statement_count": len(statements),
    }


@router.post("/{corp_id}", response_model=BankingDataResponse)
async def create_banking_data(
    corp_id: str,
    data: BankingDataCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Banking Data 생성

    새로운 기준일의 Banking Data를 생성합니다.
    """
    # Verify corporation exists
    corp_query = select(Corporation).where(Corporation.corp_id == corp_id)
    corp_result = await db.execute(corp_query)
    if not corp_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail=f"Corporation not found: {corp_id}")

    # Check if data already exists for this date
    existing_query = select(BankingData).where(
        BankingData.corp_id == corp_id,
        BankingData.data_date == data.data_date
    )
    existing_result = await db.execute(existing_query)
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"Banking data already exists for {corp_id} on {data.data_date}"
        )

    # Create new record
    banking_data = BankingData(
        corp_id=corp_id,
        data_date=data.data_date,
        loan_exposure=data.loan_exposure,
        deposit_trend=data.deposit_trend,
        card_usage=data.card_usage,
        collateral_detail=data.collateral_detail,
        trade_finance=data.trade_finance,
        financial_statements=data.financial_statements,
        risk_alerts=[],
        opportunity_signals=[],
    )

    db.add(banking_data)
    await db.commit()
    await db.refresh(banking_data)

    return banking_data


@router.put("/{corp_id}/{data_date}", response_model=BankingDataResponse)
async def update_banking_data(
    corp_id: str,
    data_date: date,
    data: BankingDataUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Banking Data 업데이트

    기존 Banking Data를 업데이트합니다.
    """
    query = select(BankingData).where(
        BankingData.corp_id == corp_id,
        BankingData.data_date == data_date
    )
    result = await db.execute(query)
    banking_data = result.scalar_one_or_none()

    if not banking_data:
        raise HTTPException(
            status_code=404,
            detail=f"Banking data not found for {corp_id} on {data_date}"
        )

    # Update fields
    if data.loan_exposure is not None:
        banking_data.loan_exposure = data.loan_exposure
    if data.deposit_trend is not None:
        banking_data.deposit_trend = data.deposit_trend
    if data.card_usage is not None:
        banking_data.card_usage = data.card_usage
    if data.collateral_detail is not None:
        banking_data.collateral_detail = data.collateral_detail
    if data.trade_finance is not None:
        banking_data.trade_finance = data.trade_finance
    if data.financial_statements is not None:
        banking_data.financial_statements = data.financial_statements

    await db.commit()
    await db.refresh(banking_data)

    return banking_data


@router.get("/summary/all", response_model=List[BankingDataSummary])
async def get_all_banking_data_summary(
    db: AsyncSession = Depends(get_db),
):
    """
    전체 기업의 Banking Data 요약 조회

    모든 기업의 최신 Banking Data 요약을 반환합니다.
    """
    # Use view for latest data per corp
    query = text("""
        SELECT bd.corp_id, bd.data_date,
               bd.loan_exposure->>'total_exposure_krw' as total_exposure,
               bd.deposit_trend->>'current_balance' as deposit_balance,
               jsonb_array_length(COALESCE(bd.risk_alerts, '[]'::jsonb)) as risk_count,
               jsonb_array_length(COALESCE(bd.opportunity_signals, '[]'::jsonb)) as opp_count
        FROM rkyc_banking_data_latest bd
        ORDER BY bd.corp_id
    """)

    result = await db.execute(query)
    rows = result.fetchall()

    summaries = []
    for row in rows:
        summaries.append(BankingDataSummary(
            corp_id=row[0],
            data_date=row[1],
            total_exposure_krw=int(row[2]) if row[2] else None,
            deposit_balance=int(row[3]) if row[3] else None,
            risk_count=row[4] or 0,
            opportunity_count=row[5] or 0,
        ))

    return summaries
