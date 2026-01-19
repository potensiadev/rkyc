"""
rKYC Corporation Schemas
Pydantic models for request/response validation (PRD 14.1.1)
"""

from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, Field


class CorporationBase(BaseModel):
    """Base corporation schema"""

    corp_name: str = Field(..., max_length=200, description="기업명")
    corp_reg_no: Optional[str] = Field(None, max_length=20, description="법인번호 (개인사업자는 NULL)")
    biz_no: Optional[str] = Field(None, max_length=12, description="사업자등록번호")
    industry_code: str = Field(..., max_length=10, description="업종코드 (예: C26)")
    ceo_name: str = Field(..., max_length=100, description="대표자명")


class CorporationCreate(CorporationBase):
    """Corporation creation request"""

    corp_id: str = Field(..., max_length=20, description="고객번호 (예: 8001-3719240)")


class CorporationUpdate(BaseModel):
    """Corporation update request"""

    corp_name: Optional[str] = Field(None, max_length=200)
    biz_no: Optional[str] = Field(None, max_length=12)
    industry_code: Optional[str] = Field(None, max_length=10)
    ceo_name: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = Field(None, description="사업장 소재지")
    hq_address: Optional[str] = Field(None, description="본점 소재지")
    founded_date: Optional[date] = Field(None, description="개업 연월일")
    biz_type: Optional[str] = Field(None, max_length=100, description="업태")
    biz_item: Optional[str] = Field(None, description="종목")
    is_corporation: Optional[bool] = Field(None, description="법인사업자 여부")


class CorporationResponse(CorporationBase):
    """Corporation response"""

    corp_id: str
    address: Optional[str] = None
    hq_address: Optional[str] = None
    founded_date: Optional[date] = None
    biz_type: Optional[str] = None
    biz_item: Optional[str] = None
    is_corporation: Optional[bool] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CorporationListResponse(BaseModel):
    """List of corporations"""

    total: int
    items: list[CorporationResponse]
