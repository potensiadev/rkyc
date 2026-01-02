"""
External Intelligence Models
보안 아키텍처: External LLM이 수집/분석한 공개 정보 저장

Tables:
- rkyc_external_news: 외부 뉴스/이벤트 원본
- rkyc_external_analysis: External LLM 분석 결과
- rkyc_industry_intel: 업종별 인텔리전스 집계
- rkyc_policy_tracker: 정책/규제 변화 추적
- rkyc_llm_audit_log: LLM 호출 감사 로그
"""

from datetime import datetime, date
from enum import Enum
from typing import Optional, List
from uuid import UUID

from sqlalchemy import (
    Column, String, Text, Boolean, Integer, DateTime, Date,
    ForeignKey, ARRAY, Numeric, CheckConstraint, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


# =====================================================
# Enums
# =====================================================

class SourceType(str, Enum):
    """뉴스 소스 타입"""
    NEWS = "NEWS"           # 일반 뉴스
    DART = "DART"           # DART 공시
    POLICY = "POLICY"       # 정책/규제
    REPORT = "REPORT"       # 산업 리포트


class Sentiment(str, Enum):
    """감성 분석 결과"""
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"


class ImpactLevel(str, Enum):
    """영향도"""
    HIGH = "HIGH"
    MED = "MED"
    LOW = "LOW"


class PolicyType(str, Enum):
    """정책 타입"""
    REGULATION = "REGULATION"     # 규정
    GUIDELINE = "GUIDELINE"       # 가이드라인
    LAW = "LAW"                   # 법률
    ANNOUNCEMENT = "ANNOUNCEMENT"  # 발표/공고


class LLMType(str, Enum):
    """LLM 타입 (보안 분류)"""
    EXTERNAL = "EXTERNAL"   # 외부 공개 데이터용
    INTERNAL = "INTERNAL"   # 내부 민감 데이터용


class DataClassification(str, Enum):
    """데이터 분류"""
    PUBLIC = "PUBLIC"           # 공개
    INTERNAL = "INTERNAL"       # 내부
    SEMI_PUBLIC = "SEMI_PUBLIC" # 준공개


# =====================================================
# Models
# =====================================================

class ExternalNews(Base):
    """외부 뉴스/이벤트 원본"""
    __tablename__ = "rkyc_external_news"

    news_id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())

    # 원본 정보
    source_type = Column(String(20), nullable=False)  # NEWS, DART, POLICY, REPORT
    source_name = Column(String(100))                  # 언론사/출처명
    original_url = Column(Text, nullable=False)
    url_hash = Column(String(64), nullable=False, unique=True)  # SHA256

    # 컨텐츠
    title = Column(String(500), nullable=False)
    content_raw = Column(Text)                         # 원문 (크롤링)
    published_at = Column(DateTime(timezone=True), nullable=False)

    # 메타데이터
    language = Column(String(10), default='ko')
    crawled_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    analyses = relationship("ExternalAnalysis", back_populates="news", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "source_type IN ('NEWS', 'DART', 'POLICY', 'REPORT')",
            name="chk_external_news_source_type"
        ),
    )


class ExternalAnalysis(Base):
    """External LLM 분석 결과"""
    __tablename__ = "rkyc_external_analysis"

    analysis_id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    news_id = Column(PGUUID(as_uuid=True), ForeignKey("rkyc_external_news.news_id", ondelete="CASCADE"), nullable=False)

    # LLM 분석 결과
    summary_ko = Column(Text, nullable=False)          # 한글 요약
    summary_en = Column(Text)                          # 영문 요약 (옵션)

    # 분류/태깅
    industry_codes = Column(ARRAY(String(10)))         # 관련 업종코드
    keywords = Column(ARRAY(Text))                     # 핵심 키워드
    entities = Column(JSONB)                           # 추출된 엔티티

    # 이벤트 분류
    event_category = Column(String(50))                # INDUSTRY_SHOCK, POLICY_CHANGE 등
    sentiment = Column(String(20))                     # POSITIVE, NEGATIVE, NEUTRAL
    impact_level = Column(String(10))                  # HIGH, MED, LOW

    # LLM 메타데이터
    llm_provider = Column(String(20), nullable=False)  # ANTHROPIC, OPENAI, PERPLEXITY
    llm_model = Column(String(50), nullable=False)
    confidence = Column(Numeric(3, 2))                 # 0.00 ~ 1.00

    # 시그널 생성 여부
    is_signal_candidate = Column(Boolean, default=False)
    signal_type_hint = Column(String(20))              # INDUSTRY, ENVIRONMENT

    analyzed_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    news = relationship("ExternalNews", back_populates="analyses")

    __table_args__ = (
        CheckConstraint(
            "sentiment IS NULL OR sentiment IN ('POSITIVE', 'NEGATIVE', 'NEUTRAL')",
            name="chk_external_analysis_sentiment"
        ),
        CheckConstraint(
            "impact_level IS NULL OR impact_level IN ('HIGH', 'MED', 'LOW')",
            name="chk_external_analysis_impact"
        ),
        CheckConstraint(
            "signal_type_hint IS NULL OR signal_type_hint IN ('INDUSTRY', 'ENVIRONMENT')",
            name="chk_external_analysis_signal_type"
        ),
    )


class IndustryIntel(Base):
    """업종별 외부 인텔리전스 집계"""
    __tablename__ = "rkyc_industry_intel"

    intel_id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    industry_code = Column(String(10), nullable=False)

    # 집계 기간
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)

    # 집계 통계
    news_count = Column(Integer, default=0)
    positive_ratio = Column(Numeric(3, 2))             # 0.00 ~ 1.00
    negative_ratio = Column(Numeric(3, 2))             # 0.00 ~ 1.00

    # LLM 생성 요약
    period_summary = Column(Text)                      # "이번 주 반도체 업종은..."
    key_events = Column(JSONB)                         # 주요 이벤트 목록
    risk_factors = Column(JSONB)                       # 식별된 리스크 요인
    opportunity_factors = Column(JSONB)                # 식별된 기회 요인

    # 메타데이터
    llm_model = Column(String(50))
    generated_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint('industry_code', 'period_start', 'period_end', name='uq_industry_intel_period'),
    )


class PolicyTracker(Base):
    """정책/규제 변화 추적"""
    __tablename__ = "rkyc_policy_tracker"

    policy_id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())

    # 정책 정보
    policy_name = Column(String(200), nullable=False)
    policy_type = Column(String(50))                   # REGULATION, GUIDELINE, LAW, ANNOUNCEMENT
    issuing_body = Column(String(100))                 # 금융위, 금감원 등

    # 영향 범위
    affected_industries = Column(ARRAY(String(10)))    # 영향받는 업종
    effective_date = Column(Date)

    # LLM 분석
    summary = Column(Text)
    impact_analysis = Column(Text)                     # 영향도 분석
    action_required = Column(Text)                     # 필요 조치 사항

    # 원본 참조
    source_url = Column(Text)
    source_document_path = Column(Text)
    news_id = Column(PGUUID(as_uuid=True), ForeignKey("rkyc_external_news.news_id"))

    # 메타데이터
    analyzed_by = Column(String(50))                   # LLM 모델
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint(
            "policy_type IS NULL OR policy_type IN ('REGULATION', 'GUIDELINE', 'LAW', 'ANNOUNCEMENT')",
            name="chk_policy_type"
        ),
    )


class LLMAuditLog(Base):
    """LLM 호출 감사 로그"""
    __tablename__ = "rkyc_llm_audit_log"

    log_id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())

    # 호출 정보
    llm_type = Column(String(20), nullable=False)      # EXTERNAL, INTERNAL
    llm_provider = Column(String(20), nullable=False)  # ANTHROPIC, OPENAI, AZURE, ONPREM
    llm_model = Column(String(50), nullable=False)

    # 요청/응답 메타데이터 (민감정보 제외)
    operation_type = Column(String(50), nullable=False)  # SIGNAL_EXTRACT, DOC_INGEST 등
    input_token_count = Column(Integer)
    output_token_count = Column(Integer)

    # 데이터 분류
    data_classification = Column(String(20), nullable=False)  # PUBLIC, INTERNAL, SEMI_PUBLIC
    contains_pii = Column(Boolean, default=False)

    # 컨텍스트
    corp_id = Column(String(20))
    job_id = Column(PGUUID(as_uuid=True))

    # 결과
    success = Column(Boolean, nullable=False)
    error_type = Column(String(50))
    response_time_ms = Column(Integer)

    # 메타데이터
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "llm_type IN ('EXTERNAL', 'INTERNAL')",
            name="chk_llm_type"
        ),
        CheckConstraint(
            "data_classification IN ('PUBLIC', 'INTERNAL', 'SEMI_PUBLIC')",
            name="chk_data_classification"
        ),
    )
