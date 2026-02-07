"""
rKYC Corporation Model
SQLAlchemy model for corp table (PRD 14.1.1)
"""

from datetime import datetime, date
from sqlalchemy import Column, String, Text, Date, Boolean, TIMESTAMP
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
    corp_reg_no = Column(String(20), nullable=True, comment="법인번호 (개인사업자는 NULL)")
    corp_name = Column(String(200), nullable=False, comment="기업명")
    biz_no = Column(String(12), nullable=True, comment="사업자등록번호")
    industry_code = Column(String(10), nullable=False, comment="업종코드 (예: C26)")
    ceo_name = Column(String(100), nullable=False, comment="대표자명")

    # 사업자등록증 추가 정보 (migration_v9)
    address = Column(Text, nullable=True, comment="사업장 소재지")
    hq_address = Column(Text, nullable=True, comment="본점 소재지 (법인만)")
    founded_date = Column(Date, nullable=True, comment="개업 연월일")
    biz_type = Column(String(100), nullable=True, comment="업태 (제조업, 건설업 등)")
    biz_item = Column(Text, nullable=True, comment="종목 (상세 업종)")
    is_corporation = Column(Boolean, default=True, comment="법인사업자 여부")

    # DART 공시 기반 정보 (migration_v12, v13 - 100% Fact 데이터)
    dart_corp_code = Column(String(8), nullable=True, comment="DART 고유번호 (8자리)")
    established_date = Column(String(8), nullable=True, comment="설립일 (YYYYMMDD) - DART 공시")
    headquarters = Column(Text, nullable=True, comment="본사 주소 - DART 공시")
    corp_class = Column(String(1), nullable=True, comment="법인 구분 (Y:유가, K:코스닥, N:코넥스, E:기타)")
    homepage_url = Column(Text, nullable=True, comment="회사 홈페이지 URL")
    jurir_no = Column(String(20), nullable=True, comment="법인등록번호 (13자리) - DART 공시")
    corp_name_eng = Column(Text, nullable=True, comment="영문 회사명 - DART 공시")
    acc_mt = Column(String(2), nullable=True, comment="결산월 (MM) - DART 공시")
    dart_updated_at = Column(TIMESTAMP(timezone=True), nullable=True, comment="DART 데이터 최종 갱신 시각")

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Corporation(corp_id='{self.corp_id}', corp_name='{self.corp_name}')>"
