# Signal Schemas
# TODO: Implement in Session 2

"""
class Evidence(BaseModel):
    url: str | None = None
    source: str | None = None
    title: str | None = None
    date: str | None = None

class SignalBase(BaseModel):
    category: str
    severity: int = Field(ge=1, le=5)
    title: str
    description: str
    evidence: list[Evidence]

class SignalResponse(SignalBase):
    id: UUID
    corporation_id: UUID
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class SignalStatusUpdate(BaseModel):
    status: str

class SignalDismiss(BaseModel):
    reason: str
"""
