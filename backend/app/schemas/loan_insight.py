"""
LoanInsight Schemas
"""

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from uuid import UUID


class LoanInsightStanceSchema(BaseModel):
    """Stance (종합 판단) 스키마"""
    level: str  # CAUTION, MONITORING, STABLE, POSITIVE
    label: str  # 한글 라벨
    color: str  # red, orange, green, blue


class LoanInsightResponse(BaseModel):
    """Loan Insight 응답 스키마"""
    insight_id: UUID
    corp_id: str

    # Stance
    stance: LoanInsightStanceSchema

    # Content
    executive_summary: Optional[str] = None  # 사업개요 + 비즈니스모델 + 핵심 시그널 요약
    narrative: str
    key_risks: List[str]
    key_opportunities: List[str] = []  # 핵심 기회 요인
    mitigating_factors: List[str]
    action_items: List[str]

    # Stats
    signal_count: int
    risk_count: int
    opportunity_count: int

    # Metadata
    generation_model: Optional[str] = None
    is_fallback: bool = False
    generated_at: datetime

    class Config:
        from_attributes = True


class LoanInsightBriefResponse(BaseModel):
    """Loan Insight 간략 응답 (목록용)"""
    corp_id: str
    stance_level: str
    stance_label: str
    narrative: str
    signal_count: int
    generated_at: datetime

    class Config:
        from_attributes = True


class LoanInsightCreateRequest(BaseModel):
    """Loan Insight 생성 요청 (Worker 내부용)"""
    corp_id: str
    stance_level: str
    stance_label: str
    stance_color: str
    narrative: str
    key_risks: List[str]
    mitigating_factors: List[str]
    action_items: List[str]
    signal_count: int = 0
    risk_count: int = 0
    opportunity_count: int = 0
    generation_model: Optional[str] = None
    generation_prompt_version: Optional[str] = None
    is_fallback: bool = False
