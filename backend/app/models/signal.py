"""
rKYC Signal Models
SQLAlchemy models for signal tables (PRD 14.7)
"""

from datetime import datetime
from uuid import UUID
from sqlalchemy import Column, String, Integer, Text, TIMESTAMP, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
import enum
from app.core.database import Base


# Enums (PRD 9장, 10장)
class SignalType(str, enum.Enum):
    """시그널 타입 (PRD 14.7)"""

    DIRECT = "DIRECT"  # 직접 리스크
    INDUSTRY = "INDUSTRY"  # 산업 리스크
    ENVIRONMENT = "ENVIRONMENT"  # 환경 리스크


class EventType(str, enum.Enum):
    """이벤트 타입 (PRD 9장 - 10종 고정)"""

    KYC_REFRESH = "KYC_REFRESH"
    INTERNAL_RISK_GRADE_CHANGE = "INTERNAL_RISK_GRADE_CHANGE"
    OVERDUE_FLAG_ON = "OVERDUE_FLAG_ON"
    LOAN_EXPOSURE_CHANGE = "LOAN_EXPOSURE_CHANGE"
    COLLATERAL_CHANGE = "COLLATERAL_CHANGE"
    OWNERSHIP_CHANGE = "OWNERSHIP_CHANGE"
    GOVERNANCE_CHANGE = "GOVERNANCE_CHANGE"
    FINANCIAL_STATEMENT_UPDATE = "FINANCIAL_STATEMENT_UPDATE"
    INDUSTRY_SHOCK = "INDUSTRY_SHOCK"
    POLICY_REGULATION_CHANGE = "POLICY_REGULATION_CHANGE"


class ImpactDirection(str, enum.Enum):
    """영향 방향"""

    RISK = "RISK"
    OPPORTUNITY = "OPPORTUNITY"
    NEUTRAL = "NEUTRAL"


class ImpactStrength(str, enum.Enum):
    """영향 강도"""

    HIGH = "HIGH"
    MED = "MED"
    LOW = "LOW"


class ConfidenceLevel(str, enum.Enum):
    """신뢰도"""

    HIGH = "HIGH"
    MED = "MED"
    LOW = "LOW"


class SignalStatus(str, enum.Enum):
    """시그널 상태 (Session 5)"""

    NEW = "NEW"  # 신규
    REVIEWED = "REVIEWED"  # 검토 완료
    DISMISSED = "DISMISSED"  # 기각


class SignalIndex(Base):
    """
    시그널 인덱스 테이블 (Dashboard 전용, 조인 금지!)
    PRD 14.7.3 - rkyc_signal_index
    """

    __tablename__ = "rkyc_signal_index"

    # Primary Key
    index_id = Column(PGUUID(as_uuid=True), primary_key=True)

    # Denormalized fields (조인 금지!)
    corp_id = Column(String(20), nullable=False)
    corp_name = Column(String(200), nullable=False)
    industry_code = Column(String(10), nullable=False)

    # Signal info
    signal_type = Column(SQLEnum(SignalType, name="signal_type_enum"), nullable=False)
    event_type = Column(SQLEnum(EventType, name="event_type_enum"), nullable=False)
    impact_direction = Column(SQLEnum(ImpactDirection, name="impact_direction_enum"), nullable=False)
    impact_strength = Column(SQLEnum(ImpactStrength, name="impact_strength_enum"), nullable=False)
    confidence = Column(SQLEnum(ConfidenceLevel, name="confidence_level"), nullable=False)

    # Content
    title = Column(String(500), nullable=False, comment="짧은 요약 제목")
    summary_short = Column(Text, nullable=True, comment="짧은 요약")
    evidence_count = Column(Integer, nullable=False)

    # Timestamps
    detected_at = Column(TIMESTAMP(timezone=True), nullable=False, comment="정렬 기준")
    last_updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)

    # Foreign key reference (for detail lookup only)
    signal_id = Column(PGUUID(as_uuid=True), nullable=False)

    # Status fields (Session 5)
    signal_status = Column(
        SQLEnum(SignalStatus, name="signal_status_enum"),
        default=SignalStatus.NEW,
        nullable=True,
    )
    reviewed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    dismissed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    dismiss_reason = Column(Text, nullable=True)

    def __repr__(self):
        return f"<SignalIndex(corp_name='{self.corp_name}', event_type='{self.event_type}')>"


class Signal(Base):
    """
    시그널 원본 테이블 (PRD 14.7.1)
    rkyc_signal - 시그널 상세 정보 저장
    """

    __tablename__ = "rkyc_signal"

    # Primary Key
    signal_id = Column(PGUUID(as_uuid=True), primary_key=True)

    # Corp info
    corp_id = Column(String(20), nullable=False)

    # Signal info
    signal_type = Column(SQLEnum(SignalType, name="signal_type_enum"), nullable=False)
    event_type = Column(SQLEnum(EventType, name="event_type_enum"), nullable=False)
    event_signature = Column(String(64), nullable=False, comment="sha256 해시 (중복 방지)")
    snapshot_version = Column(Integer, nullable=False)

    # Impact
    impact_direction = Column(
        SQLEnum(ImpactDirection, name="impact_direction_enum"), nullable=False
    )
    impact_strength = Column(
        SQLEnum(ImpactStrength, name="impact_strength_enum"), nullable=False
    )
    confidence = Column(
        SQLEnum(ConfidenceLevel, name="confidence_level"), nullable=False
    )

    # Content
    summary = Column(Text, nullable=False, comment="전체 요약")

    # Status fields (Session 5)
    signal_status = Column(
        SQLEnum(SignalStatus, name="signal_status_enum"),
        default=SignalStatus.NEW,
        nullable=True,
    )
    reviewed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    dismissed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    dismiss_reason = Column(Text, nullable=True)

    # Timestamps
    last_updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)

    def __repr__(self):
        return f"<Signal(corp_id='{self.corp_id}', event_type='{self.event_type}')>"


class Evidence(Base):
    """
    시그널 근거 테이블 (PRD 14.7.2)
    rkyc_evidence - 시그널별 출처/근거 정보
    """

    __tablename__ = "rkyc_evidence"

    # Primary Key
    evidence_id = Column(PGUUID(as_uuid=True), primary_key=True)

    # Foreign key to signal
    signal_id = Column(PGUUID(as_uuid=True), nullable=False)

    # Evidence info
    evidence_type = Column(
        String(20), nullable=False, comment="INTERNAL_FIELD, DOC, EXTERNAL"
    )
    ref_type = Column(
        String(20), nullable=False, comment="SNAPSHOT_KEYPATH, DOC_PAGE, URL"
    )
    ref_value = Column(Text, nullable=False, comment="JSON Pointer or URL")
    snippet = Column(Text, nullable=True, comment="관련 텍스트 스니펫")
    meta = Column(JSONB, nullable=True, comment="추가 메타데이터")

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)

    def __repr__(self):
        return f"<Evidence(signal_id='{self.signal_id}', type='{self.evidence_type}')>"
