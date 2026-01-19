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


class ProfileStatusEnum(str, Enum):
    """프로파일 상태"""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    UNKNOWN = "UNKNOWN"


# ============================================================================
# Field Provenance Schemas (Anti-Hallucination Layer 4)
# ============================================================================


class FieldProvenanceResponse(BaseModel):
    """개별 필드의 출처 정보"""
    source_url: Optional[str] = None
    excerpt: Optional[str] = Field(None, description="출처에서 발췌한 텍스트 (최대 200자)")
    confidence: ConfidenceLevelEnum
    extraction_date: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================================
# Profile Response Schemas
# ============================================================================


class CorpProfileResponse(BaseModel):
    """
    기업 프로파일 응답 (API)

    Includes:
    - Business profile data
    - Confidence levels (overall and per-field)
    - Source URLs for traceability
    - Fallback/validation status
    """
    profile_id: UUID
    corp_id: str

    # Business Profile Fields
    business_summary: str = Field(..., description="주요 사업 요약")
    revenue_krw: Optional[int] = Field(None, description="연 매출 (원화)")
    export_ratio_pct: Optional[int] = Field(None, ge=0, le=100, description="수출 비중 (%)")

    # Exposure Information
    country_exposure: dict = Field(default_factory=dict, description="국가별 노출 비중")
    key_materials: list[str] = Field(default_factory=list, description="주요 원자재 목록")
    key_customers: list[str] = Field(default_factory=list, description="주요 고객사 목록")
    overseas_operations: list[str] = Field(default_factory=list, description="해외 법인/공장")

    # Confidence & Attribution (Anti-Hallucination Layer 2)
    profile_confidence: ConfidenceLevelEnum
    field_confidences: dict[str, str] = Field(
        default_factory=dict,
        description="필드별 신뢰도 (예: {'export_ratio_pct': 'HIGH'})"
    )
    source_urls: list[str] = Field(default_factory=list, description="출처 URL 목록")

    # Fallback & Validation Flags
    is_fallback: bool = Field(False, description="업종 기본 프로파일 사용 여부")
    search_failed: bool = Field(False, description="검색 실패 여부")
    validation_warnings: list[str] = Field(default_factory=list, description="검증 경고")

    # Status
    status: ProfileStatusEnum = ProfileStatusEnum.ACTIVE

    # TTL Information
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
