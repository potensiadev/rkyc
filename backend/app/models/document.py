"""
Document Models
SQLAlchemy models for rkyc_document, rkyc_document_page, rkyc_fact tables
"""

import enum
from datetime import datetime
from uuid import UUID
from typing import Optional, Any

from sqlalchemy import (
    Column, String, Integer, Text, DateTime, ForeignKey,
    Numeric, Enum as SQLEnum, JSON
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class DocType(str, enum.Enum):
    """Document type enum (PRD 6.2)"""
    BIZ_REG = "BIZ_REG"              # 사업자등록증
    REGISTRY = "REGISTRY"            # 법인 등기부등본
    SHAREHOLDERS = "SHAREHOLDERS"    # 주주명부
    AOI = "AOI"                      # 정관
    FIN_STATEMENT = "FIN_STATEMENT"  # 재무제표 요약


class IngestStatus(str, enum.Enum):
    """Document ingest status"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"


class ConfidenceLevel(str, enum.Enum):
    """Confidence level for extracted facts"""
    HIGH = "HIGH"
    MED = "MED"
    LOW = "LOW"


class Document(Base):
    """
    rkyc_document table model
    Stores document metadata for submitted corporate documents
    """
    __tablename__ = "rkyc_document"

    doc_id = Column(PGUUID(as_uuid=True), primary_key=True)
    corp_id = Column(String(20), ForeignKey("corp.corp_id"), nullable=False)
    doc_type = Column(SQLEnum(DocType, name="doc_type_enum", create_type=False), nullable=False)
    storage_provider = Column(String(20), default="FILESYS")
    storage_path = Column(Text)
    file_hash = Column(String(64))  # For change detection
    page_count = Column(Integer)
    captured_at = Column(DateTime(timezone=True))
    ingest_status = Column(
        SQLEnum(IngestStatus, name="ingest_status_enum", create_type=False),
        default=IngestStatus.PENDING
    )
    last_ingested_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    pages = relationship("DocumentPage", back_populates="document", cascade="all, delete-orphan")
    facts = relationship("Fact", back_populates="document", cascade="all, delete-orphan")


class DocumentPage(Base):
    """
    rkyc_document_page table model
    Stores page-level metadata for multi-page documents
    """
    __tablename__ = "rkyc_document_page"

    page_id = Column(PGUUID(as_uuid=True), primary_key=True)
    doc_id = Column(PGUUID(as_uuid=True), ForeignKey("rkyc_document.doc_id"), nullable=False)
    page_no = Column(Integer, nullable=False)  # 1-based
    image_path = Column(Text)
    width = Column(Integer)
    height = Column(Integer)

    # Relationships
    document = relationship("Document", back_populates="pages")


class Fact(Base):
    """
    rkyc_fact table model
    Stores extracted facts from documents using Vision LLM
    """
    __tablename__ = "rkyc_fact"

    fact_id = Column(PGUUID(as_uuid=True), primary_key=True)
    corp_id = Column(String(20), ForeignKey("corp.corp_id"), nullable=False)
    doc_id = Column(PGUUID(as_uuid=True), ForeignKey("rkyc_document.doc_id"), nullable=False)
    doc_type = Column(SQLEnum(DocType, name="doc_type_enum", create_type=False), nullable=False)
    fact_type = Column(String(50), nullable=False)  # SHAREHOLDER, OFFICER, CAPITAL, etc.
    field_key = Column(String(100), nullable=False)
    field_value_text = Column(Text)
    field_value_num = Column(Numeric)
    field_value_json = Column(JSON)
    confidence = Column(
        SQLEnum(ConfidenceLevel, name="confidence_level", create_type=False),
        nullable=False
    )
    evidence_snippet = Column(Text)  # <= 400 chars
    evidence_page_no = Column(Integer)
    evidence_bbox = Column(JSON)  # {"x": 0, "y": 0, "width": 100, "height": 50}
    extracted_by = Column(String(100))  # model/version
    extracted_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    document = relationship("Document", back_populates="facts")
