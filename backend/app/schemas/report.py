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

# Corp Profile for Report (공급망, 해외사업, 거시요인 등)
class ReportSupplyChain(BaseModel):
    key_suppliers: List[str] = Field(default_factory=list)
    supplier_countries: Dict[str, int] = Field(default_factory=dict)  # country -> percentage
    single_source_risk: List[str] = Field(default_factory=list)
    material_import_ratio_pct: Optional[int] = None

class ReportOverseasBusiness(BaseModel):
    subsidiaries: List[Dict[str, str]] = Field(default_factory=list)  # [{name, country}]
    manufacturing_countries: List[str] = Field(default_factory=list)

class ReportCorpProfile(BaseModel):
    business_summary: Optional[str] = None
    revenue_krw: Optional[int] = None
    export_ratio_pct: Optional[int] = None
    country_exposure: List[str] = Field(default_factory=list)
    key_materials: List[str] = Field(default_factory=list)
    key_customers: List[str] = Field(default_factory=list)
    supply_chain: Optional[ReportSupplyChain] = None
    overseas_business: Optional[ReportOverseasBusiness] = None
    competitors: List[str] = Field(default_factory=list)
    macro_factors: List[Dict[str, str]] = Field(default_factory=list)  # [{factor, impact}]
    shareholders: List[Dict[str, Any]] = Field(default_factory=list)  # [{name, ownership_pct}]
    profile_confidence: Optional[str] = None

class FullReportResponse(BaseModel):
    corporation: CorporationInfo
    summary_stats: ReportSignalSummary
    signals: List[SignalDetailResponse]
    evidence_list: List[EvidenceResponse] # Flattened list of top evidences for the summary section
    loan_insight: Optional[LoanInsightResponse] = None
    corp_profile: Optional[ReportCorpProfile] = None  # NEW: 공급망, 해외사업 등
    snapshot_data: Optional[Dict[str, Any]] = None # Detailed snapshot if needed
    generated_at: datetime
