"""
LoanInsight Model - Pre-generated Loan Insight for CorporateDetailPage
"""

from sqlalchemy import Column, String, Text, Boolean, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class LoanInsight(Base):
    """
    Pre-generated Loan Insight table.
    Generated at Worker INSIGHT pipeline stage.
    One insight per corp_id (UPSERT pattern).
    """
    __tablename__ = "rkyc_loan_insight"

    # PK
    insight_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # FK: 기업
    corp_id = Column(String(20), ForeignKey("corp.corp_id", ondelete="CASCADE"), nullable=False, unique=True)

    # Stance (종합 판단)
    stance_level = Column(String(20), nullable=False, default="STABLE")  # CAUTION, MONITORING, STABLE, POSITIVE
    stance_label = Column(String(50), nullable=False, default="중립/안정적")
    stance_color = Column(String(20), nullable=False, default="green")

    # Narrative (종합 소견)
    narrative = Column(Text, nullable=False, default="")

    # Key Risks (핵심 리스크 요인) - JSON array of strings
    key_risks = Column(JSONB, nullable=False, default=list)

    # Mitigating Factors (리스크 상쇄/기회 요인) - JSON array of strings
    mitigating_factors = Column(JSONB, nullable=False, default=list)

    # Action Items (심사역 확인 체크리스트) - JSON array of strings
    action_items = Column(JSONB, nullable=False, default=list)

    # Generation metadata
    signal_count = Column(Integer, nullable=False, default=0)
    risk_count = Column(Integer, nullable=False, default=0)
    opportunity_count = Column(Integer, nullable=False, default=0)

    # LLM metadata
    generation_model = Column(String(100), nullable=True)
    generation_prompt_version = Column(String(20), nullable=True)
    is_fallback = Column(Boolean, nullable=False, default=False)

    # Timestamps
    generated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<LoanInsight(corp_id={self.corp_id}, stance={self.stance_level})>"
