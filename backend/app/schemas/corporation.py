# Corporation Schemas
# TODO: Implement in Session 2

"""
class CorporationBase(BaseModel):
    biz_no: str
    corp_name: str
    industry: str | None = None

class CorporationCreate(CorporationBase):
    pass

class CorporationUpdate(BaseModel):
    corp_name: str | None = None
    status: str | None = None
    industry: str | None = None

class CorporationResponse(CorporationBase):
    id: UUID
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
"""
