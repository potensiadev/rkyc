"""
Banking Data Model
PRD: Internal Banking Data Integration v1.1

은행 내부 거래 데이터 모델
- 여신/수신/카드/담보/무역금융/재무제표
"""

from datetime import date, datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy import Column, String, Date, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class BankingData(Base):
    """은행 내부 거래 데이터"""

    __tablename__ = "rkyc_banking_data"

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    corp_id = Column(String(20), ForeignKey("corp.corp_id", ondelete="CASCADE"), nullable=False)

    # 메타데이터
    data_date = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"))
    updated_at = Column(DateTime(timezone=True), server_default=text("NOW()"))

    # JSON 데이터 블록
    loan_exposure = Column(JSONB)           # 여신 현황
    deposit_trend = Column(JSONB)           # 수신 추이
    card_usage = Column(JSONB)              # 법인카드
    collateral_detail = Column(JSONB)       # 담보 상세
    trade_finance = Column(JSONB)           # 무역금융
    financial_statements = Column(JSONB)    # 재무제표 (DART)

    # 자동 생성된 시그널
    risk_alerts = Column(JSONB, server_default=text("'[]'::jsonb"))
    opportunity_signals = Column(JSONB, server_default=text("'[]'::jsonb"))

    # Relationships
    corporation = relationship("Corporation", back_populates="banking_data")

    def __repr__(self):
        return f"<BankingData(corp_id={self.corp_id}, data_date={self.data_date})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "corp_id": self.corp_id,
            "data_date": self.data_date.isoformat() if self.data_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "loan_exposure": self.loan_exposure,
            "deposit_trend": self.deposit_trend,
            "card_usage": self.card_usage,
            "collateral_detail": self.collateral_detail,
            "trade_finance": self.trade_finance,
            "financial_statements": self.financial_statements,
            "risk_alerts": self.risk_alerts or [],
            "opportunity_signals": self.opportunity_signals or [],
        }
