"""
rKYC Corporation Schemas
Pydantic models for request/response validation (PRD 14.1.1)
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class CorporationBase(BaseModel):
    """Base corporation schema"""

    corp_name: str = Field(..., max_length=200, description="기업명")
    corp_reg_no: str = Field(..., max_length=20, description="법인번호")
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


class CorporationResponse(CorporationBase):
    """Corporation response"""

    corp_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CorporationListResponse(BaseModel):
    """List of corporations"""

    total: int
    items: list[CorporationResponse]
