"""
rKYC Report API Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.core.database import get_db
from app.models.signal import Signal, Evidence, SignalIndex
from app.schemas.report import FullReportResponse, CorporationInfo, ReportSignalSummary, LoanInsightResponse
from app.schemas.signal import SignalDetailResponse, EvidenceResponse, SignalStatusEnum
from app.worker.generators.loan_insight import LoanInsightGenerator

router = APIRouter()
loan_insight_generator = LoanInsightGenerator()

@router.get("/corporation/{corp_id}", response_model=FullReportResponse)
async def get_corporation_report(
    corp_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get full report data for a corporation.
    Includes:
    - Basic Corp Info (from Signals mostly, or separate query if needed)
    - Summary Statistics
    - Full Signal List with Evidence
    - AI Loan Insight
    """
    
    # 1. Fetch Signals with Evidence
    # We join SignalIndex and Signal to get full details + status
    # And we prefetch evidences to avoid N+1 (though standard ORM lazy load might be N+1, so we do explicit load)
    
    # Fetch Signals
    query = (
        select(SignalIndex, Signal)
        .outerjoin(Signal, Signal.signal_id == SignalIndex.signal_id)
        .where(SignalIndex.corp_id == corp_id)
        .order_by(SignalIndex.detected_at.desc())
    )
    result = await db.execute(query)
    signal_rows = result.all()
    
    if not signal_rows:
        # If no signals, we might skip or return empty report
        # We need at least corp name for the header. Usually we'd query Corp table.
        # For now, if no signals, we return placeholder or look up Corp table.
        # Assuming at least one signal or we handle empty gracefully.
        pass

    # Fetch Evidences for all these signals
    signal_ids = [row[0].signal_id for row in signal_rows]
    evidences_map = {}
    
    if signal_ids:
        ev_query = select(Evidence).where(Evidence.signal_id.in_(signal_ids)).order_by(Evidence.created_at.desc())
        ev_result = await db.execute(ev_query)
        all_evidences = ev_result.scalars().all()
        
        for ev in all_evidences:
            if ev.signal_id not in evidences_map:
                evidences_map[ev.signal_id] = []
            evidences_map[ev.signal_id].append(ev)

    # Construct Signal Responses & Stats
    signals_response: List[SignalDetailResponse] = []
    
    summary_stats = {
        "total": 0, "direct": 0, "industry": 0, "environment": 0, 
        "risk": 0, "opportunity": 0, "neutral": 0
    }
    
    corp_info = None
    
    # Collect flat list of top evidences for the "Key Evidence" section
    flattened_evidences: List[EvidenceResponse] = []

    for idx, (idx_obj, signal_obj) in enumerate(signal_rows):
        # Infer corp info from first signal if not set (fallback)
        if idx == 0 and not corp_info:
            corp_info = CorporationInfo(
                id=idx_obj.corp_id,
                name=idx_obj.corp_name,
                business_number="", # Need corp table access for this usually
                industry=idx_obj.industry_code, # Placeholder
                industry_code=idx_obj.industry_code
            )

        # Update stats
        summary_stats["total"] += 1
        summary_stats[idx_obj.signal_type.lower()] += 1
        summary_stats[idx_obj.impact_direction.lower()] += 1
        
        # Build Detail Response
        status_val = signal_obj.signal_status if signal_obj else SignalStatusEnum.NEW
        evs = evidences_map.get(idx_obj.signal_id, [])
        
        # Map Evidences to Schema
        ev_responses = [
            EvidenceResponse(
                evidence_id=e.evidence_id,
                signal_id=e.signal_id,
                evidence_type=e.evidence_type,
                ref_type=e.ref_type,
                ref_value=e.ref_value,
                snippet=e.snippet,
                meta=e.meta,
                created_at=e.created_at
            ) for e in evs
        ]
        
        # Add to flattened list (limit to top 10 recent overall?)
        # Let's just add all and frontend slices, or we select top relevant.
        # For now add all.
        flattened_evidences.extend(ev_responses)
        
        detail = SignalDetailResponse(
            signal_id=idx_obj.signal_id,
            corp_id=idx_obj.corp_id,
            corp_name=idx_obj.corp_name,
            industry_code=idx_obj.industry_code,
            signal_type=idx_obj.signal_type,
            event_type=idx_obj.event_type,
            impact_direction=idx_obj.impact_direction,
            impact_strength=idx_obj.impact_strength,
            confidence=idx_obj.confidence,
            title=idx_obj.title,
            summary=signal_obj.summary if signal_obj else idx_obj.summary_short or "",
            summary_short=idx_obj.summary_short,
            signal_status=status_val,
            evidence_count=idx_obj.evidence_count,
            detected_at=idx_obj.detected_at,
            reviewed_at=signal_obj.reviewed_at if signal_obj else None,
            dismissed_at=signal_obj.dismissed_at if signal_obj else None,
            dismiss_reason=signal_obj.dismiss_reason if signal_obj else None,
            evidences=ev_responses
        )
        signals_response.append(detail)

    # 2. Generate or Fetch Loan Insight
    # We pass the constructed signal objects (schema format is fine if generator supports it, or raw models)
    # The generator expects Signal model objects. We constructed our own schema. 
    # Let's modify generator or pass the 'idx_obj's.
    # Actually generator expects `app.models.signal.Signal` (or compatible). 
    # We have `signal_rows` which are (SignalIndex, Signal). 
    # We should reconstruct a list of Objects that have the attributes needed by the prompt generator.
    # The prompt generator uses: signal_type, impact_direction, title, impact_strength, summary_short.
    # SignalIndex has all these.
    
    # We'll use the indices for generation context
    index_objects = [row[0] for row in signal_rows]
    
    # Fallback corp name if still None
    c_name = corp_id
    i_name = "Unknown"
    if index_objects:
        c_name = index_objects[0].corp_name
        i_name = index_objects[0].industry_code # approximate
    
    loan_insight = await loan_insight_generator.generate(
        corp_name=c_name, 
        industry_name=i_name, 
        signals=index_objects
    )

    # 3. Handle Empty Corp Info if no signals
    if not corp_info:
        # Should probably fetch from DB explicitly if no signals found
        # But for this implementation we assume signals exist or we return minimal
        corp_info = CorporationInfo(
            id=corp_id,
            name=c_name,
            business_number="",
            industry=i_name,
            industry_code=""
        )

    return FullReportResponse(
        corporation=corp_info,
        summary_stats=ReportSignalSummary(**summary_stats),
        signals=signals_response,
        evidence_list=flattened_evidences, # This now contains actual objects
        loan_insight=loan_insight,
        generated_at=datetime.now()
    )
