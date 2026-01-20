"""
rKYC Signal Enriched Schemas
Extended schemas for rich signal detail display
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field
from enum import Enum

from app.schemas.signal import (
    SignalDetailResponse,
    EvidenceResponse,
    SignalStatusEnum,
)
from app.models.signal import (
    SignalType,
    EventType,
    ImpactDirection,
    ImpactStrength,
    ConfidenceLevel,
)


# =============================================================================
# Enums
# =============================================================================

class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    PARTIAL = "PARTIAL"
    UNVERIFIED = "UNVERIFIED"
    CONFLICTING = "CONFLICTING"


class SourceCredibility(str, Enum):
    OFFICIAL = "OFFICIAL"  # 공시, 정부 발표
    MAJOR_MEDIA = "MAJOR_MEDIA"  # 주요 경제지
    MINOR_MEDIA = "MINOR_MEDIA"  # 일반 뉴스
    UNKNOWN = "UNKNOWN"


class ImpactAnalysisType(str, Enum):
    FINANCIAL = "FINANCIAL"
    CREDIT = "CREDIT"
    OPERATIONAL = "OPERATIONAL"
    REGULATORY = "REGULATORY"


class RelationType(str, Enum):
    SAME_CORP = "SAME_CORP"
    SAME_INDUSTRY = "SAME_INDUSTRY"
    CAUSAL = "CAUSAL"
    TEMPORAL = "TEMPORAL"


# =============================================================================
# Sub-schemas
# =============================================================================

class SimilarCaseResponse(BaseModel):
    """유사 과거 케이스"""
    id: UUID
    similarity_score: float = Field(..., ge=0, le=1)
    corp_id: Optional[str] = None
    corp_name: Optional[str] = None
    industry_code: Optional[str] = None
    signal_type: Optional[str] = None
    event_type: Optional[str] = None
    summary: Optional[str] = None
    outcome: Optional[str] = None  # 과거 케이스의 결과

    class Config:
        from_attributes = True


class VerificationResponse(BaseModel):
    """소스 검증 결과"""
    id: UUID
    verification_type: str  # SOURCE_CHECK, CROSS_REFERENCE, FACT_VALIDATION
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    verification_status: VerificationStatus
    confidence_contribution: Optional[float] = None
    details: Optional[Dict[str, Any]] = None
    verified_at: datetime

    class Config:
        from_attributes = True


class ImpactAnalysisResponse(BaseModel):
    """영향도 분석 결과"""
    id: UUID
    analysis_type: ImpactAnalysisType
    metric_name: str
    current_value: Optional[float] = None
    projected_impact: Optional[float] = None
    impact_direction: Optional[str] = None  # INCREASE, DECREASE, STABLE
    impact_percentage: Optional[float] = None
    industry_avg: Optional[float] = None
    industry_percentile: Optional[int] = Field(None, ge=1, le=100)
    reasoning: Optional[str] = None
    data_source: Optional[str] = None

    class Config:
        from_attributes = True


class RelatedSignalResponse(BaseModel):
    """관련 시그널"""
    signal_id: UUID
    relation_type: RelationType
    relation_strength: Optional[float] = None
    corp_id: str
    corp_name: str
    signal_type: SignalType
    event_type: EventType
    impact_direction: ImpactDirection
    impact_strength: ImpactStrength
    title: str
    summary_short: Optional[str] = None
    detected_at: datetime
    description: Optional[str] = None

    class Config:
        from_attributes = True


class CorpContextResponse(BaseModel):
    """기업 컨텍스트 (Corp Profile 요약)"""
    corp_id: str
    corp_name: str
    industry_code: str
    industry_name: Optional[str] = None

    # 기본 정보
    revenue_krw: Optional[int] = None
    employee_count: Optional[int] = None
    export_ratio_pct: Optional[float] = None

    # 위험 노출
    country_exposure: Optional[List[str]] = None
    key_materials: Optional[List[str]] = None
    key_customers: Optional[List[str]] = None

    # 공급망
    supply_chain_risk: Optional[str] = None  # LOW, MED, HIGH

    # 내부 상태
    internal_risk_grade: Optional[str] = None
    overdue_flag: Optional[bool] = None
    total_exposure_krw: Optional[int] = None

    # 프로필 메타
    profile_confidence: Optional[str] = None
    profile_updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EnrichedEvidenceResponse(EvidenceResponse):
    """확장된 Evidence 응답"""
    source_credibility: Optional[SourceCredibility] = None
    verification_status: Optional[str] = None
    retrieved_at: Optional[datetime] = None

    # 추가 컨텍스트
    source_domain: Optional[str] = None  # URL에서 추출한 도메인
    is_primary_source: bool = False  # 1차 출처 여부


# =============================================================================
# Main Enriched Response
# =============================================================================

class SignalEnrichedDetailResponse(BaseModel):
    """
    Signal 풍부한 상세 응답

    기존 SignalDetailResponse + 추가 분석 데이터
    """
    # 기본 시그널 정보
    signal_id: UUID
    corp_id: str
    corp_name: str
    industry_code: str
    signal_type: SignalType
    event_type: EventType
    impact_direction: ImpactDirection
    impact_strength: ImpactStrength
    confidence: ConfidenceLevel
    title: str
    summary: str
    summary_short: Optional[str] = None
    signal_status: SignalStatusEnum
    evidence_count: int
    detected_at: datetime
    reviewed_at: Optional[datetime] = None
    dismissed_at: Optional[datetime] = None
    dismiss_reason: Optional[str] = None

    # 확장된 Evidence 목록
    evidences: List[EnrichedEvidenceResponse] = []

    # LLM 분석 메타데이터
    analysis_reasoning: Optional[str] = None  # LLM이 시그널을 추출한 근거
    llm_model: Optional[str] = None

    # 기업 컨텍스트 (Corp Profile 요약)
    corp_context: Optional[CorpContextResponse] = None

    # 유사 과거 케이스
    similar_cases: List[SimilarCaseResponse] = []

    # 다중 소스 검증 결과
    verifications: List[VerificationResponse] = []

    # 영향도 분석
    impact_analysis: List[ImpactAnalysisResponse] = []

    # 관련 시그널
    related_signals: List[RelatedSignalResponse] = []

    # 인사이트 (해당 시그널 관련 브리핑 발췌)
    insight_excerpt: Optional[str] = None

    class Config:
        from_attributes = True


# =============================================================================
# Dashboard용 집계 응답
# =============================================================================

class SignalAnalyticsSummary(BaseModel):
    """시그널 분석 요약 통계"""
    total_signals: int
    signals_by_type: Dict[str, int]  # DIRECT, INDUSTRY, ENVIRONMENT
    signals_by_direction: Dict[str, int]  # RISK, OPPORTUNITY, NEUTRAL
    signals_by_strength: Dict[str, int]  # HIGH, MED, LOW

    # 검증 통계
    verified_count: int
    partially_verified_count: int
    unverified_count: int
    avg_confidence_score: float

    # 유사 케이스 통계
    cases_with_similar_history: int
    avg_similarity_score: float

    # 트렌드
    signals_last_7_days: int
    signals_last_30_days: int
    risk_trend: str  # INCREASING, STABLE, DECREASING


class CorpRiskProfile(BaseModel):
    """기업 리스크 프로파일 요약"""
    corp_id: str
    corp_name: str
    industry_code: str

    # 시그널 요약
    active_signals: int
    high_priority_signals: int
    risk_signals: int
    opportunity_signals: int

    # 리스크 점수 (0-100)
    overall_risk_score: int
    credit_risk_score: int
    operational_risk_score: int
    regulatory_risk_score: int

    # 기회 점수 (0-100)
    opportunity_score: int
    growth_potential_score: int

    # 업종 대비
    industry_risk_percentile: int  # 1-100 (낮을수록 위험)
    industry_opportunity_percentile: int

    # 권고 사항
    key_recommendations: List[str]
    monitoring_items: List[str]

    last_analyzed_at: datetime
