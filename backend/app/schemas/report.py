"""
rKYC Report Schemas
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field

from app.schemas.signal import SignalDetailResponse, EvidenceResponse
from app.models.signal import ConfidenceLevel

# Loan Insight Schemas

class LoanInsightStance(BaseModel):
    label: str  # e.g., "주의 요망 (Caution)"
    level: str  # e.g., "CAUTION", "MONITORING", "STABLE", "POSITIVE"
    color: str  # e.g., "orange", "yellow", "green"

class LoanInsightResponse(BaseModel):
    stance: LoanInsightStance
    narrative: str
    key_risks: List[str] = Field(default_factory=list)
    mitigating_factors: List[str] = Field(default_factory=list)
    action_items: List[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.now)

# Full Report Response

class CorporationInfo(BaseModel):
    id: str
    name: str
    business_number: str
    industry: str
    industry_code: str
    ceo: Optional[str] = None
    address: Optional[str] = None
    has_loan: bool = False
    internal_rating: Optional[str] = None

class ReportSignalSummary(BaseModel):
    total: int
    direct: int
    industry: int
    environment: int
    risk: int
    opportunity: int
    neutral: int

class FullReportResponse(BaseModel):
    corporation: CorporationInfo
    summary_stats: ReportSignalSummary
    signals: List[SignalDetailResponse]
    evidence_list: List[EvidenceResponse] # Flattened list of top evidences for the summary section
    loan_insight: Optional[LoanInsightResponse] = None
    snapshot_data: Optional[Dict[str, Any]] = None # Detailed snapshot if needed
    generated_at: datetime
