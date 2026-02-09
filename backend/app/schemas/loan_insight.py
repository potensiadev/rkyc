"""
LoanInsight Schemas
PRD v1.0: 핵심 리스크/기회 요인 구조화
"""

from pydantic import BaseModel
from typing import List, Optional, Union, Any
from datetime import datetime
from uuid import UUID


class LoanInsightStanceSchema(BaseModel):
    """Stance (종합 판단) 스키마"""
    level: str  # CAUTION, MONITORING, STABLE, POSITIVE
    label: str  # 한글 라벨
    color: str  # red, orange, green, blue


class KeyFactorSchema(BaseModel):
    """핵심 리스크/기회 요인 스키마 (PRD v1.0)"""
    priority: int  # 1-5 우선순위
    text: str  # 분석 내용
    source_signal_id: Optional[str] = None  # 근거 시그널 ID (클릭 시 상세 이동)
    _corrected: Optional[bool] = None  # 숫자 보정 여부
    _auto_generated: Optional[bool] = None  # Fallback 생성 여부

    class Config:
        from_attributes = True


class LoanInsightResponse(BaseModel):
    """Loan Insight 응답 스키마"""
    insight_id: UUID
    corp_id: str

    # Stance
    stance: LoanInsightStanceSchema

    # Content
    executive_summary: Optional[str] = None
    narrative: str
    # PRD v1.0: 구조화된 핵심 요인 (기존 string[] 호환)
    key_risks: Union[List[KeyFactorSchema], List[str], List[Any]]
    key_opportunities: Union[List[KeyFactorSchema], List[str], List[Any]] = []
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
    key_risks: Union[List[KeyFactorSchema], List[str], List[Any]]
    key_opportunities: Union[List[KeyFactorSchema], List[str], List[Any]] = []
    mitigating_factors: List[str]
    action_items: List[str]
    signal_count: int = 0
    risk_count: int = 0
    opportunity_count: int = 0
    generation_model: Optional[str] = None
    generation_prompt_version: Optional[str] = None
    is_fallback: bool = False
