"""
rKYC Corp Profile Models
SQLAlchemy models for corp profile table (PRD: Corp Profiling Pipeline)

Anti-Hallucination Architecture:
- Layer 2: Confidence & Attribution (field_confidences, source_urls)
- Layer 4: Audit Trail (raw_search_result, field_provenance)
"""

from datetime import datetime, UTC
from sqlalchemy import (
    Column,
    String,
    BigInteger,
    Integer,
    Text,
    Boolean,
    TIMESTAMP,
    Enum as SQLEnum,
    ARRAY,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from app.core.database import Base
from app.models.signal import ConfidenceLevel


class ProfileStatus(str):
    """프로파일 상태"""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    UNKNOWN = "UNKNOWN"


class CorpProfile(Base):
    """
    기업 프로파일 테이블 (Anti-Hallucination Audit Trail 포함)
    rkyc_corp_profile

    Purpose:
    - Store structured business profile for ENVIRONMENT signal grounding
    - Track complete provenance for every extracted field
    - Enable conditional query selection based on profile data
    """

    __tablename__ = "rkyc_corp_profile"

    # =========================================================================
    # Primary Key
    # =========================================================================
    profile_id = Column(PGUUID(as_uuid=True), primary_key=True)

    # =========================================================================
    # Foreign Key
    # =========================================================================
    corp_id = Column(
        String(20),
        nullable=False,
        unique=True,
        comment="기업 ID (corp 테이블 참조)",
    )

    # =========================================================================
    # Extracted Profile Fields
    # =========================================================================
    business_summary = Column(
        Text,
        nullable=False,
        comment="주요 사업 요약 (100자 이내)",
    )
    revenue_krw = Column(
        BigInteger,
        nullable=True,
        comment="연 매출 (원화)",
    )
    export_ratio_pct = Column(
        Integer,
        nullable=True,
        comment="수출 비중 (%, 0-100)",
    )

    # =========================================================================
    # Exposure Information
    # =========================================================================
    country_exposure = Column(
        JSONB,
        nullable=False,
        default={},
        comment='국가별 노출 비중 (예: {"중국": 20, "미국": 30})',
    )
    key_materials = Column(
        ARRAY(Text),
        nullable=False,
        default=[],
        comment='주요 원자재 목록 (예: ["실리콘 웨이퍼", "PCB"])',
    )
    key_customers = Column(
        ARRAY(Text),
        nullable=False,
        default=[],
        comment='주요 고객사 목록 (예: ["삼성전자"])',
    )
    overseas_operations = Column(
        ARRAY(Text),
        nullable=False,
        default=[],
        comment='해외 법인/공장 (예: ["베트남 하노이 공장"])',
    )

    # =========================================================================
    # Confidence & Attribution (Anti-Hallucination Layer 2)
    # =========================================================================
    profile_confidence = Column(
        SQLEnum(ConfidenceLevel, name="confidence_level"),
        nullable=False,
        comment="전체 프로파일 신뢰도 (HIGH/MED/LOW)",
    )
    field_confidences = Column(
        JSONB,
        nullable=False,
        default={},
        comment='필드별 신뢰도 (예: {"export_ratio_pct": "HIGH"})',
    )
    source_urls = Column(
        ARRAY(Text),
        nullable=False,
        default=[],
        comment="출처 URL 목록",
    )

    # =========================================================================
    # AUDIT TRAIL (Anti-Hallucination Layer 4 - Critical)
    # =========================================================================
    raw_search_result = Column(
        JSONB,
        nullable=True,
        comment="원본 Perplexity 응답 (추적용, 수정 금지)",
    )
    field_provenance = Column(
        JSONB,
        nullable=False,
        default={},
        comment="필드별 출처 매핑 (source_url, excerpt, confidence, extraction_date)",
    )
    extraction_model = Column(
        String(100),
        nullable=True,
        comment="추출에 사용된 LLM 모델",
    )
    extraction_prompt_version = Column(
        String(20),
        nullable=True,
        default="v1.0",
        comment="프롬프트 버전 (재현성 보장)",
    )

    # =========================================================================
    # Fallback & Validation Flags
    # =========================================================================
    is_fallback = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="업종 기본 프로파일 사용 여부",
    )
    search_failed = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Perplexity 검색 실패 여부",
    )
    validation_warnings = Column(
        ARRAY(Text),
        nullable=False,
        default=[],
        comment="CorpProfileValidator 경고 목록",
    )

    # =========================================================================
    # Status
    # =========================================================================
    status = Column(
        String(20),
        nullable=False,
        default="ACTIVE",
        comment="프로파일 상태 (ACTIVE/INACTIVE/UNKNOWN)",
    )

    # =========================================================================
    # TTL Management
    # =========================================================================
    fetched_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        comment="수집 시점",
    )
    expires_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        comment="만료 시점 (TTL, 기본 7일)",
    )

    # =========================================================================
    # Timestamps
    # =========================================================================
    created_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    def __repr__(self):
        return (
            f"<CorpProfile(corp_id='{self.corp_id}', "
            f"confidence='{self.profile_confidence}', "
            f"is_fallback={self.is_fallback})>"
        )

    @property
    def is_expired(self) -> bool:
        """프로파일 TTL 만료 여부 확인"""
        if self.expires_at is None:
            return True
        return datetime.now(UTC) > self.expires_at

    def get_field_confidence(self, field_name: str) -> str:
        """특정 필드의 신뢰도 조회"""
        return self.field_confidences.get(field_name, "LOW")

    def get_field_provenance(self, field_name: str) -> dict | None:
        """특정 필드의 출처 정보 조회"""
        return self.field_provenance.get(field_name)

    def has_country_exposure(self, country: str) -> bool:
        """특정 국가 노출 여부 확인"""
        return country in (self.country_exposure or {})

    def get_country_exposure_pct(self, country: str) -> int | None:
        """특정 국가 노출 비중 조회"""
        return (self.country_exposure or {}).get(country)

    def to_dict(self) -> dict:
        """프로파일을 딕셔너리로 변환"""
        return {
            "profile_id": str(self.profile_id) if self.profile_id else None,
            "corp_id": self.corp_id,
            "business_summary": self.business_summary,
            "revenue_krw": self.revenue_krw,
            "export_ratio_pct": self.export_ratio_pct,
            "country_exposure": self.country_exposure or {},
            "key_materials": list(self.key_materials or []),
            "key_customers": list(self.key_customers or []),
            "overseas_operations": list(self.overseas_operations or []),
            "profile_confidence": self.profile_confidence.value if self.profile_confidence else None,
            "is_fallback": self.is_fallback,
            "is_expired": self.is_expired,
        }
