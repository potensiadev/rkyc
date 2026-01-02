"""
Document Schemas
Pydantic schemas for document-related API endpoints
"""

from datetime import datetime
from uuid import UUID
from typing import Optional, Any

from pydantic import BaseModel, Field

from app.models.document import DocType, IngestStatus, ConfidenceLevel


# =============================================================================
# Document Schemas
# =============================================================================

class DocumentBase(BaseModel):
    """Base document schema"""
    corp_id: str
    doc_type: DocType
    storage_provider: str = "FILESYS"
    storage_path: Optional[str] = None


class DocumentCreate(DocumentBase):
    """Schema for creating a document"""
    pass


class DocumentResponse(DocumentBase):
    """Schema for document response"""
    doc_id: UUID
    file_hash: Optional[str] = None
    page_count: Optional[int] = None
    captured_at: Optional[datetime] = None
    ingest_status: IngestStatus = IngestStatus.PENDING
    last_ingested_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """Schema for document list response"""
    documents: list[DocumentResponse]
    total: int


# =============================================================================
# Document Page Schemas
# =============================================================================

class DocumentPageResponse(BaseModel):
    """Schema for document page response"""
    page_id: UUID
    doc_id: UUID
    page_no: int
    image_path: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None

    class Config:
        from_attributes = True


# =============================================================================
# Fact Schemas
# =============================================================================

class FactBase(BaseModel):
    """Base fact schema"""
    fact_type: str
    field_key: str
    field_value_text: Optional[str] = None
    field_value_num: Optional[float] = None
    field_value_json: Optional[dict] = None
    confidence: ConfidenceLevel


class FactResponse(FactBase):
    """Schema for fact response"""
    fact_id: UUID
    corp_id: str
    doc_id: UUID
    doc_type: DocType
    evidence_snippet: Optional[str] = None
    evidence_page_no: Optional[int] = None
    evidence_bbox: Optional[dict] = None
    extracted_by: Optional[str] = None
    extracted_at: datetime

    class Config:
        from_attributes = True


class FactListResponse(BaseModel):
    """Schema for fact list response"""
    facts: list[FactResponse]
    total: int


# =============================================================================
# Document Ingest Schemas
# =============================================================================

class DocumentIngestRequest(BaseModel):
    """Schema for document ingest request"""
    corp_id: str
    doc_type: DocType
    image_base64: str = Field(..., description="Base64 encoded document image")
    page_no: int = Field(default=1, ge=1, description="Page number (1-based)")


class DocumentIngestResponse(BaseModel):
    """Schema for document ingest response"""
    doc_id: UUID
    ingest_status: IngestStatus
    facts_extracted: int
    message: str


# =============================================================================
# Extracted Facts from Vision LLM
# =============================================================================

class ExtractedFactItem(BaseModel):
    """Single extracted fact from Vision LLM"""
    fact_type: str = Field(..., description="SHAREHOLDER, OFFICER, CAPITAL, BIZ_INFO, etc.")
    field_key: str = Field(..., description="Field name/key")
    field_value: str | float | dict = Field(..., description="Extracted value")
    confidence: ConfidenceLevel = Field(..., description="Extraction confidence")
    evidence_snippet: str = Field(..., max_length=400, description="Evidence text snippet")


class ExtractedFactsResponse(BaseModel):
    """Response from Vision LLM fact extraction"""
    doc_type: DocType
    facts: list[ExtractedFactItem]
    model_used: str
    extraction_time_ms: int


# =============================================================================
# Document Status Schemas
# =============================================================================

class DocumentStatusResponse(BaseModel):
    """Schema for document processing status"""
    doc_id: UUID
    corp_id: str
    doc_type: DocType
    ingest_status: IngestStatus
    page_count: Optional[int] = None
    facts_count: int = 0
    last_ingested_at: Optional[datetime] = None
    error_message: Optional[str] = None


# =============================================================================
# Document Upload Schemas
# =============================================================================

class DocumentUploadResponse(BaseModel):
    """Schema for document upload response"""
    doc_id: UUID
    corp_id: str
    doc_type: DocType
    file_name: str
    file_size: int
    storage_path: str
    ingest_status: IngestStatus
    message: str


class DocumentUploadWithProcessResponse(BaseModel):
    """Schema for document upload with immediate processing"""
    doc_id: UUID
    corp_id: str
    doc_type: DocType
    file_name: str
    ingest_status: IngestStatus
    facts_extracted: int = 0
    facts: list[FactResponse] = []
    processing_time_ms: int = 0
    message: str
