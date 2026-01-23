"""
rKYC Report API Endpoints
Loan Insight는 Worker에서 사전 생성됨 (LLM 실시간 호출 제거)
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.models.signal import Signal, Evidence, SignalIndex
from app.schemas.report import FullReportResponse, CorporationInfo, ReportSignalSummary, LoanInsightResponse, LoanInsightStance
from app.schemas.signal import SignalDetailResponse, EvidenceResponse, SignalStatusEnum

router = APIRouter()

@router.get("/corporation/{corp_id}", response_model=FullReportResponse)
async def get_corporation_report(
    corp_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get full report data for a corporation.
    Optimized: SELECT only required columns, limit evidence count.
    """

    # 1. Fetch Corp Info first (faster than extracting from signals)
    corp_query = text("""
        SELECT corp_id, corp_name, biz_no, industry_code
        FROM corp
        WHERE corp_id = :corp_id
        LIMIT 1
    """)
    corp_result = await db.execute(corp_query, {"corp_id": corp_id})
    corp_row = corp_result.fetchone()

    # 2. Optimized Signal Query - SELECT only needed columns from SignalIndex
    # Skip Signal table join if status is also in SignalIndex
    signal_query = text("""
        SELECT
            si.signal_id, si.corp_id, si.corp_name, si.industry_code,
            si.signal_type, si.event_type, si.impact_direction, si.impact_strength,
            si.confidence, si.title, si.summary_short, si.evidence_count, si.detected_at,
            s.summary, s.signal_status, s.reviewed_at, s.dismissed_at, s.dismiss_reason
        FROM rkyc_signal_index si
        LEFT JOIN rkyc_signal s ON s.signal_id = si.signal_id
        WHERE si.corp_id = :corp_id
        ORDER BY si.detected_at DESC
        LIMIT 50
    """)
    result = await db.execute(signal_query, {"corp_id": corp_id})
    signal_rows = result.fetchall()

    # 3. Fetch Evidences - limit to 3 per signal for performance
    signal_ids = [row.signal_id for row in signal_rows]
    evidences_map = {}

    if signal_ids:
        # Use ROW_NUMBER to limit evidences per signal
        ev_query = text("""
            WITH ranked_evidence AS (
                SELECT *,
                    ROW_NUMBER() OVER (PARTITION BY signal_id ORDER BY created_at DESC) as rn
                FROM rkyc_evidence
                WHERE signal_id = ANY(:signal_ids)
            )
            SELECT evidence_id, signal_id, evidence_type, ref_type, ref_value, snippet, meta, created_at
            FROM ranked_evidence
            WHERE rn <= 3
            ORDER BY created_at DESC
        """)
        ev_result = await db.execute(ev_query, {"signal_ids": signal_ids})
        all_evidences = ev_result.fetchall()

        for ev in all_evidences:
            if ev.signal_id not in evidences_map:
                evidences_map[ev.signal_id] = []
            evidences_map[ev.signal_id].append(ev)

    # 4. Construct Corp Info from direct query (faster than extracting from signals)
    if corp_row:
        corp_info = CorporationInfo(
            id=corp_row.corp_id,
            name=corp_row.corp_name,
            business_number=corp_row.biz_no or "",
            industry=corp_row.industry_code or "",
            industry_code=corp_row.industry_code or ""
        )
    elif signal_rows:
        # Fallback to first signal if corp not found
        first_signal = signal_rows[0]
        corp_info = CorporationInfo(
            id=first_signal.corp_id,
            name=first_signal.corp_name,
            business_number="",
            industry=first_signal.industry_code or "",
            industry_code=first_signal.industry_code or ""
        )
    else:
        corp_info = CorporationInfo(
            id=corp_id,
            name=corp_id,
            business_number="",
            industry="",
            industry_code=""
        )

    # 5. Construct Signal Responses & Stats
    signals_response: List[SignalDetailResponse] = []
    summary_stats = {
        "total": 0, "direct": 0, "industry": 0, "environment": 0,
        "risk": 0, "opportunity": 0, "neutral": 0
    }
    flattened_evidences: List[EvidenceResponse] = []

    for row in signal_rows:
        # Update stats
        summary_stats["total"] += 1
        signal_type_lower = (row.signal_type or "").lower()
        impact_lower = (row.impact_direction or "neutral").lower()
        if signal_type_lower in summary_stats:
            summary_stats[signal_type_lower] += 1
        if impact_lower in summary_stats:
            summary_stats[impact_lower] += 1

        # Build Evidence Responses
        evs = evidences_map.get(row.signal_id, [])
        ev_responses = [
            EvidenceResponse(
                evidence_id=e.evidence_id,
                signal_id=e.signal_id,
                evidence_type=e.evidence_type,
                ref_type=e.ref_type,
                ref_value=e.ref_value,
                snippet=e.snippet,
                meta=e.meta if hasattr(e, 'meta') else None,
                created_at=e.created_at
            ) for e in evs
        ]
        flattened_evidences.extend(ev_responses)

        # Build Signal Detail Response
        detail = SignalDetailResponse(
            signal_id=row.signal_id,
            corp_id=row.corp_id,
            corp_name=row.corp_name,
            industry_code=row.industry_code,
            signal_type=row.signal_type,
            event_type=row.event_type,
            impact_direction=row.impact_direction,
            impact_strength=row.impact_strength,
            confidence=row.confidence,
            title=row.title,
            summary=row.summary or row.summary_short or "",
            summary_short=row.summary_short,
            signal_status=row.signal_status or SignalStatusEnum.NEW,
            evidence_count=row.evidence_count or 0,
            detected_at=row.detected_at,
            reviewed_at=row.reviewed_at,
            dismissed_at=row.dismissed_at,
            dismiss_reason=row.dismiss_reason,
            evidences=ev_responses
        )
        signals_response.append(detail)

    # 6. Fetch Pre-generated Loan Insight from DB (NO LLM call)
    loan_insight = await _fetch_loan_insight_from_db(db, corp_id)

    # 7. Limit flattened evidences to top 10 for report summary
    flattened_evidences = flattened_evidences[:10]

    return FullReportResponse(
        corporation=corp_info,
        summary_stats=ReportSignalSummary(**summary_stats),
        signals=signals_response,
        evidence_list=flattened_evidences, # This now contains actual objects
        loan_insight=loan_insight,
        generated_at=datetime.now()
    )


async def _fetch_loan_insight_from_db(
    db: AsyncSession,
    corp_id: str,
) -> Optional[LoanInsightResponse]:
    """
    Fetch pre-generated Loan Insight from DB.
    Returns None if not found (analysis not run yet).
    """
    result = await db.execute(
        text("""
            SELECT
                stance_level, stance_label, stance_color,
                narrative, key_risks, mitigating_factors, action_items
            FROM rkyc_loan_insight
            WHERE corp_id = :corp_id
        """),
        {"corp_id": corp_id},
    )
    row = result.fetchone()

    if not row:
        # Return default insight if not found
        return LoanInsightResponse(
            stance=LoanInsightStance(
                label="분석 대기",
                level="STABLE",
                color="grey",
            ),
            narrative="Loan Insight가 아직 생성되지 않았습니다. 분석 실행 후 확인해 주세요.",
            key_risks=[],
            mitigating_factors=[],
            action_items=["분석 실행 필요"],
        )

    return LoanInsightResponse(
        stance=LoanInsightStance(
            label=row.stance_label,
            level=row.stance_level,
            color=row.stance_color,
        ),
        narrative=row.narrative,
        key_risks=row.key_risks or [],
        mitigating_factors=row.mitigating_factors or [],
        action_items=row.action_items or [],
    )
