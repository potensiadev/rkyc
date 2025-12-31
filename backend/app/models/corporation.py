"""
rKYC Corporation Model
SQLAlchemy model for corp table (PRD 14.1.1)
"""

from datetime import datetime
from sqlalchemy import Column, String, TIMESTAMP
from app.core.database import Base


class Corporation(Base):
    """
    기업 마스터 테이블
    PRD 14.1.1 - corp table
    """

    __tablename__ = "corp"

    # Primary Key
    corp_id = Column(String(20), primary_key=True, comment="고객번호 (예: 8001-3719240)")

    # 기업 정보
    corp_reg_no = Column(String(20), nullable=False, comment="법인번호")
    corp_name = Column(String(200), nullable=False, comment="기업명")
    biz_no = Column(String(12), nullable=True, comment="사업자등록번호 (가라 허용)")
    industry_code = Column(String(10), nullable=False, comment="업종코드 (예: C26)")
    ceo_name = Column(String(100), nullable=False, comment="대표자명")

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Corporation(corp_id='{self.corp_id}', corp_name='{self.corp_name}')>"
