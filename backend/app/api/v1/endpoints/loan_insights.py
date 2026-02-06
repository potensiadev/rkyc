"""
Loan Insight API Endpoints
Pre-generated Loan Insight 조회

조건부 적용:
- 여신 금액이 있는 경우에만 Loan Insight 제공
- 여신이 없으면 "당행 여신이 없습니다" 메시지 반환
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional, Tuple
from datetime import datetime

from app.core.database import get_db
from app.schemas.loan_insight import LoanInsightResponse, LoanInsightStanceSchema

router = APIRouter()


async def check_loan_status(db: AsyncSession, corp_id: str) -> Tuple[bool, Optional[int]]:
    """
    Internal Snapshot에서 여신 상태 확인.

    Returns:
        Tuple[has_loan, total_exposure_krw]
    """
    result = await db.execute(
        text("""
            SELECT
                isl.snapshot_json->'credit'->>'has_loan' as has_loan,
                (isl.snapshot_json->'credit'->'loan_summary'->>'total_exposure_krw')::BIGINT as total_exposure_krw
            FROM rkyc_internal_snapshot_latest latest
            JOIN rkyc_internal_snapshot isl ON latest.snapshot_id = isl.snapshot_id
            WHERE latest.corp_id = :corp_id
        """),
        {"corp_id": corp_id},
    )
    row = result.fetchone()

    if not row:
        return False, None

    has_loan = row.has_loan == 'true' if row.has_loan else False
    total_exposure = row.total_exposure_krw

    # has_loan이 True이거나 total_exposure가 0보다 크면 여신 있음
    return (has_loan or (total_exposure is not None and total_exposure > 0)), total_exposure


@router.get("/{corp_id}")
async def get_loan_insight(
    corp_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get pre-generated Loan Insight for a corporation.

    조건부 응답:
    1. 여신이 없는 경우: has_loan=false, message="당행 여신이 없습니다"
    2. 여신이 있고 Insight가 있는 경우: 정상 Loan Insight 반환
    3. 여신이 있고 Insight가 없는 경우: has_loan=true, insight_exists=false (분석 대기 중)

    NOTE: "AI 분석이 아직 생성되지 않았습니다"는 절대 표시하지 않음
    """
    # Step 1: 여신 상태 확인
    has_loan, total_exposure = await check_loan_status(db, corp_id)

    if not has_loan:
        # 여신이 없는 경우 - 별도 응답 (200 OK)
        return JSONResponse(
            status_code=200,
            content={
                "has_loan": False,
                "total_exposure_krw": 0,
                "message": "당행 여신이 없습니다",
                "insight": None,
            }
        )

    # Step 2: 여신이 있는 경우 - Loan Insight 조회
    result = await db.execute(
        text("""
            SELECT
                insight_id, corp_id,
                stance_level, stance_label, stance_color,
                executive_summary, narrative, key_risks, key_opportunities, mitigating_factors, action_items,
                signal_count, risk_count, opportunity_count,
                generation_model, is_fallback, generated_at
            FROM rkyc_loan_insight
            WHERE corp_id = :corp_id
        """),
        {"corp_id": corp_id},
    )
    row = result.fetchone()

    if not row:
        # 여신은 있지만 Insight가 없는 경우 (분석 대기 중)
        return JSONResponse(
            status_code=200,
            content={
                "has_loan": True,
                "total_exposure_krw": total_exposure,
                "insight_exists": False,
                "message": "분석 중입니다. 잠시 후 다시 확인해 주세요.",
                "insight": None,
            }
        )

    # 정상 Loan Insight 반환
    return {
        "has_loan": True,
        "total_exposure_krw": total_exposure,
        "insight_exists": True,
        "insight": {
            "insight_id": str(row.insight_id),
            "corp_id": row.corp_id,
            "stance": {
                "level": row.stance_level,
                "label": row.stance_label,
                "color": row.stance_color,
            },
            "executive_summary": row.executive_summary,
            "narrative": row.narrative,
            "key_risks": row.key_risks or [],
            "key_opportunities": row.key_opportunities or [],
            "mitigating_factors": row.mitigating_factors or [],
            "action_items": row.action_items or [],
            "signal_count": row.signal_count,
            "risk_count": row.risk_count,
            "opportunity_count": row.opportunity_count,
            "generation_model": row.generation_model,
            "is_fallback": row.is_fallback,
            "generated_at": row.generated_at.isoformat() if row.generated_at else None,
        }
    }


@router.get("/{corp_id}/exists")
async def check_loan_insight_exists(
    corp_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Check if Loan Insight exists for a corporation.

    Returns:
        exists: bool
        generated_at: datetime or null
    """
    result = await db.execute(
        text("""
            SELECT generated_at, stance_level
            FROM rkyc_loan_insight
            WHERE corp_id = :corp_id
        """),
        {"corp_id": corp_id},
    )
    row = result.fetchone()

    if row:
        return {
            "exists": True,
            "generated_at": row.generated_at,
            "stance_level": row.stance_level,
        }
    else:
        return {
            "exists": False,
            "generated_at": None,
            "stance_level": None,
        }


@router.get("/")
async def get_all_loan_insight_summaries(
    db: AsyncSession = Depends(get_db),
):
    """
    Get all Loan Insight summaries for Signal Inbox display.
    Returns stance level, label, color, and one-line summary for each corporation.
    """
    result = await db.execute(
        text("""
            SELECT
                corp_id,
                stance_level,
                stance_label,
                stance_color,
                executive_summary,
                risk_count,
                opportunity_count,
                generated_at
            FROM rkyc_loan_insight
            ORDER BY generated_at DESC
        """)
    )
    rows = result.fetchall()

    return {
        "insights": [
            {
                "corp_id": row.corp_id,
                "stance_level": row.stance_level,
                "stance_label": row.stance_label,
                "stance_color": row.stance_color,
                "executive_summary": row.executive_summary,
                "risk_count": row.risk_count,
                "opportunity_count": row.opportunity_count,
                "generated_at": row.generated_at.isoformat() if row.generated_at else None,
            }
            for row in rows
        ]
    }
