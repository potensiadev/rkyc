"""
Loan Insight API Endpoints
Pre-generated Loan Insight 조회
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.schemas.loan_insight import LoanInsightResponse, LoanInsightStanceSchema

router = APIRouter()


@router.get("/{corp_id}", response_model=LoanInsightResponse)
async def get_loan_insight(
    corp_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get pre-generated Loan Insight for a corporation.

    Returns 404 if no Loan Insight exists (analysis not run yet).
    """
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
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "LOAN_INSIGHT_NOT_FOUND",
                "message": f"Loan Insight not found for corp_id={corp_id}. Run analysis first.",
            },
        )

    return LoanInsightResponse(
        insight_id=row.insight_id,
        corp_id=row.corp_id,
        stance=LoanInsightStanceSchema(
            level=row.stance_level,
            label=row.stance_label,
            color=row.stance_color,
        ),
        executive_summary=row.executive_summary,
        narrative=row.narrative,
        key_risks=row.key_risks or [],
        key_opportunities=row.key_opportunities or [],
        mitigating_factors=row.mitigating_factors or [],
        action_items=row.action_items or [],
        signal_count=row.signal_count,
        risk_count=row.risk_count,
        opportunity_count=row.opportunity_count,
        generation_model=row.generation_model,
        is_fallback=row.is_fallback,
        generated_at=row.generated_at,
    )


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
