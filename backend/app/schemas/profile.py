"""
rKYC Corp Profile Schemas
Pydantic models for corp profile request/response

Anti-Hallucination Architecture:
- Field-level confidence tracking
- Provenance information for traceability
- Source URL attribution
"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field
from enum import Enum


class ConfidenceLevelEnum(str, Enum):
    """신뢰도 레벨"""
    HIGH = "HIGH"
    MED = "MED"
    LOW = "LOW"
    NONE = "NONE"
    CACHED = "CACHED"
    STALE = "STALE"


class ProfileStatusEnum(str, Enum):
    """프로파일 상태"""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    UNKNOWN = "UNKNOWN"


# ============================================================================
# Nested Types (PRD v1.2)
# ============================================================================


class ExecutiveSchema(BaseModel):
    """임원 정보"""
    name: Optional[str] = None
    position: Optional[str] = None
    tenure_years: Optional[int] = None


class FinancialSnapshotSchema(BaseModel):
    """연도별 재무 스냅샷"""
    year: Optional[int] = None
    revenue_krw: Optional[int] = None
    operating_profit_krw: Optional[int] = None
    net_profit_krw: Optional[int] = None
    total_assets_krw: Optional[int] = None
    total_liabilities_krw: Optional[int] = None
    export_ratio_pct: Optional[int] = None


class CompetitorSchema(BaseModel):
    """경쟁사 정보"""
    name: Optional[str] = None
    market_share_pct: Optional[float] = None
    relationship: Optional[str] = None  # DIRECT, INDIRECT


class MacroFactorSchema(BaseModel):
    """거시 요인"""
    factor: Optional[str] = None
    impact: Optional[str] = None  # POSITIVE, NEGATIVE, NEUTRAL
    description: Optional[str] = None


class SupplyChainSchema(BaseModel):
    """공급망 정보 (PRD v1.2)"""
    key_suppliers: list[str] = Field(default_factory=list)
    supplier_countries: dict[str, int] = Field(default_factory=dict)  # {"중국": 60, "일본": 30}
    single_source_risk: list[str] = Field(default_factory=list)
    material_import_ratio_pct: Optional[int] = None


class OverseasSubsidiarySchema(BaseModel):
    """해외 법인"""
    name: Optional[str] = None
    country: Optional[str] = None
    business_type: Optional[str] = None
    ownership_pct: Optional[float] = None


class OverseasBusinessSchema(BaseModel):
    """해외 사업 (PRD v1.2)"""
    subsidiaries: list[OverseasSubsidiarySchema] = Field(default_factory=list)
    manufacturing_countries: list[str] = Field(default_factory=list)


class ShareholderSchema(BaseModel):
    """주주 정보"""
    name: Optional[str] = None
    ownership_pct: Optional[float] = None
    is_largest: Optional[bool] = None
    relationship: Optional[str] = None  # FOUNDER, INSTITUTION, FOREIGN, OTHER


class ConsensusMetadataSchema(BaseModel):
    """Consensus 메타데이터 (PRD v1.2)"""
    consensus_at: Optional[datetime] = None
    perplexity_success: Optional[bool] = False
    gemini_success: Optional[bool] = False
    claude_success: Optional[bool] = False
    total_fields: Optional[int] = 0
    matched_fields: Optional[int] = 0
    discrepancy_fields: Optional[int] = 0
    enriched_fields: Optional[int] = 0
    overall_confidence: Optional[str] = "LOW"
    fallback_layer: Optional[str | int] = None  # Can be string (enum name) or int
    retry_count: Optional[int] = 0
    error_messages: Optional[list[str]] = Field(default_factory=list)


# ============================================================================
# Field Provenance Schemas (Anti-Hallucination Layer 4)
# ============================================================================


class FieldProvenanceResponse(BaseModel):
    """개별 필드의 출처 정보"""
    source_url: Optional[str] = None
    excerpt: Optional[str] = Field(None, description="출처에서 발췌한 텍스트 (최대 200자)")
    confidence: Optional[ConfidenceLevelEnum] = ConfidenceLevelEnum.LOW
    extraction_date: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================================
# Profile Response Schemas
# ============================================================================


class CorpProfileResponse(BaseModel):
    """
    기업 프로파일 응답 (API) - PRD v1.2

    Includes:
    - Business profile data (expanded)
    - Supply chain & overseas business
    - Confidence levels (overall and per-field)
    - Source URLs for traceability
    - Fallback/validation status
    - Consensus metadata
    """
    profile_id: UUID
    corp_id: str

    # ========================================================================
    # Basic Info (PRD v1.2 확장)
    # ========================================================================
    business_summary: Optional[str] = Field(None, description="주요 사업 요약")
    ceo_name: Optional[str] = Field(None, description="대표이사 이름")
    employee_count: Optional[int] = Field(None, description="임직원 수")
    founded_year: Optional[int] = Field(None, description="설립 연도")
    headquarters: Optional[str] = Field(None, description="본사 소재지")
    executives: list[ExecutiveSchema] = Field(default_factory=list, description="주요 임원")

    # ========================================================================
    # Business Overview
    # ========================================================================
    industry_overview: Optional[str] = Field(None, description="업종 개요")
    business_model: Optional[str] = Field(None, description="비즈니스 모델")

    # ========================================================================
    # Financial
    # ========================================================================
    revenue_krw: Optional[int] = Field(None, description="연 매출 (원화)")
    export_ratio_pct: Optional[int] = Field(None, ge=0, le=100, description="수출 비중 (%)")
    financial_history: list[FinancialSnapshotSchema] = Field(default_factory=list, description="3개년 재무 스냅샷")

    # ========================================================================
    # Exposure Information
    # ========================================================================
    country_exposure: dict = Field(default_factory=dict, description="국가별 노출 비중")
    key_materials: list[str] = Field(default_factory=list, description="주요 원자재 목록")
    key_customers: list[str] = Field(default_factory=list, description="주요 고객사 목록")
    overseas_operations: list[str] = Field(default_factory=list, description="해외 법인/공장 (레거시)")

    # ========================================================================
    # Value Chain (PRD v1.2)
    # ========================================================================
    competitors: list[CompetitorSchema] = Field(default_factory=list, description="경쟁사")
    macro_factors: list[MacroFactorSchema] = Field(default_factory=list, description="거시 요인")

    # ========================================================================
    # Supply Chain (PRD v1.2)
    # ========================================================================
    supply_chain: SupplyChainSchema = Field(default_factory=SupplyChainSchema, description="공급망 정보")

    # ========================================================================
    # Overseas Business (PRD v1.2)
    # ========================================================================
    overseas_business: OverseasBusinessSchema = Field(default_factory=OverseasBusinessSchema, description="해외 사업")

    # ========================================================================
    # Shareholders
    # ========================================================================
    shareholders: list[ShareholderSchema] = Field(default_factory=list, description="주주 정보")

    # ========================================================================
    # Consensus Metadata (PRD v1.2)
    # ========================================================================
    consensus_metadata: ConsensusMetadataSchema = Field(default_factory=ConsensusMetadataSchema, description="Consensus 메타데이터")

    # ========================================================================
    # Confidence & Attribution (Anti-Hallucination Layer 2)
    # ========================================================================
    profile_confidence: ConfidenceLevelEnum = ConfidenceLevelEnum.LOW
    field_confidences: dict[str, str] = Field(
        default_factory=dict,
        description="필드별 신뢰도 (예: {'export_ratio_pct': 'HIGH'})"
    )
    source_urls: list[str] = Field(default_factory=list, description="출처 URL 목록")

    # ========================================================================
    # Fallback & Validation Flags
    # ========================================================================
    is_fallback: bool = Field(False, description="업종 기본 프로파일 사용 여부")
    search_failed: bool = Field(False, description="검색 실패 여부")
    validation_warnings: list[str] = Field(default_factory=list, description="검증 경고")

    # ========================================================================
    # Status & TTL
    # ========================================================================
    status: ProfileStatusEnum = ProfileStatusEnum.ACTIVE
    fetched_at: datetime
    expires_at: datetime
    is_expired: bool = Field(False, description="TTL 만료 여부")

    class Config:
        from_attributes = True


class CorpProfileDetailResponse(CorpProfileResponse):
    """
    기업 프로파일 상세 응답 (Provenance 포함)

    Includes all base profile data plus:
    - Per-field provenance (source URL, excerpt, confidence)
    - Extraction metadata (model, prompt version)
    """
    # Audit Trail (Anti-Hallucination Layer 4)
    field_provenance: dict[str, FieldProvenanceResponse] = Field(
        default_factory=dict,
        description="필드별 출처 정보"
    )
    extraction_model: Optional[str] = Field(None, description="추출에 사용된 LLM 모델")
    extraction_prompt_version: Optional[str] = Field(None, description="프롬프트 버전")

    created_at: datetime
    updated_at: datetime


# ============================================================================
# Profile Request Schemas
# ============================================================================


class ProfileRefreshRequest(BaseModel):
    """프로파일 강제 갱신 요청"""
    force: bool = Field(
        default=False,
        description="TTL 무시하고 강제 갱신"
    )


# ============================================================================
# Conditional Query Selection Schemas
# ============================================================================


class QueryCondition(BaseModel):
    """조건부 쿼리 조건"""
    field: str
    operator: str  # ">=", "==", "in", "contains_key", "is_not_empty"
    value: Optional[str | int | list] = None
    is_met: bool = False


class SelectedQueryResponse(BaseModel):
    """조건부 쿼리 선택 결과"""
    category: str = Field(..., description="쿼리 카테고리 (예: FX_RISK, GEOPOLITICAL)")
    conditions_met: list[QueryCondition] = Field(
        default_factory=list,
        description="충족된 조건 목록"
    )


class ProfileQuerySelectionResponse(BaseModel):
    """프로파일 기반 쿼리 선택 결과"""
    corp_id: str
    profile_confidence: ConfidenceLevelEnum
    selected_queries: list[str] = Field(
        default_factory=list,
        description="선택된 ENVIRONMENT 쿼리 카테고리"
    )
    query_details: list[SelectedQueryResponse] = Field(
        default_factory=list,
        description="각 쿼리별 조건 상세"
    )
    skipped_queries: list[str] = Field(
        default_factory=list,
        description="조건 미충족으로 제외된 쿼리"
    )


# ============================================================================
# Profile Evidence Schema (for Signal linkage)
# ============================================================================


class ProfileEvidenceRequest(BaseModel):
    """
    프로파일 데이터를 Signal Evidence로 연결

    Used when creating ENVIRONMENT signals based on profile data.
    """
    signal_id: UUID
    field_path: str = Field(
        ...,
        description="JSON Pointer 형식 (예: /export_ratio_pct, /country_exposure/중국)"
    )


class ProfileEvidenceResponse(BaseModel):
    """프로파일 Evidence 응답"""
    evidence_id: UUID
    signal_id: UUID
    evidence_type: str = "CORP_PROFILE"
    ref_type: str = "PROFILE_KEYPATH"
    ref_value: str  # JSON Pointer path
    snippet: str  # Human-readable summary
    meta: dict = Field(
        default_factory=dict,
        description="source_url, confidence, field_value 포함"
    )
    created_at: datetime


# ============================================================================
# Validation Response Schemas
# ============================================================================


class ProfileValidationResult(BaseModel):
    """프로파일 검증 결과"""
    is_valid: bool
    errors: list[str] = Field(default_factory=list, description="검증 오류")
    warnings: list[str] = Field(default_factory=list, description="검증 경고")
    field_issues: dict[str, list[str]] = Field(
        default_factory=dict,
        description="필드별 이슈"
    )
