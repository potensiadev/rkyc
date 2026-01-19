"""
Documents API Endpoints
PRD 16.3 기준 - 문서 관리 및 추출된 Facts 조회
"""

import base64
import hashlib
import os
import time
from datetime import datetime, UTC
from pathlib import Path
from uuid import UUID, uuid4
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.models.document import Document, DocumentPage, Fact, DocType, IngestStatus
from app.schemas.document import (
    DocumentResponse,
    DocumentListResponse,
    DocumentPageResponse,
    FactListResponse,
    FactResponse,
    DocumentStatusResponse,
    DocumentIngestRequest,
    DocumentIngestResponse,
    DocumentUploadResponse,
    DocumentUploadWithProcessResponse,
)

# Document storage configuration
DOCUMENT_STORAGE_PATH = Path(os.getenv("DOCUMENT_STORAGE_PATH", "./data/documents"))
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf", ".tiff", ".tif"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

router = APIRouter()


@router.get(
    "/corp/{corp_id}/documents",
    response_model=DocumentListResponse,
    summary="기업 문서 목록 조회",
)
async def get_corporation_documents(
    corp_id: str,
    doc_type: Optional[DocType] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    특정 기업의 제출 문서 목록을 조회합니다.

    - **corp_id**: 기업 ID (필수)
    - **doc_type**: 문서 타입 필터 (선택)
    """
    query = select(Document).where(Document.corp_id == corp_id)

    if doc_type:
        query = query.where(Document.doc_type == doc_type)

    query = query.order_by(Document.created_at.desc())

    result = await db.execute(query)
    documents = result.scalars().all()

    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(doc) for doc in documents],
        total=len(documents),
    )


@router.get(
    "/{doc_id}/status",
    response_model=DocumentStatusResponse,
    summary="문서 처리 상태 조회",
)
async def get_document_status(
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    문서의 처리 상태를 조회합니다.

    - **doc_id**: 문서 ID (필수)
    """
    # Get document
    result = await db.execute(
        select(Document).where(Document.doc_id == doc_id)
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {doc_id} not found",
        )

    # Count facts
    facts_result = await db.execute(
        select(func.count()).select_from(Fact).where(Fact.doc_id == doc_id)
    )
    facts_count = facts_result.scalar() or 0

    return DocumentStatusResponse(
        doc_id=document.doc_id,
        corp_id=document.corp_id,
        doc_type=document.doc_type,
        ingest_status=document.ingest_status,
        page_count=document.page_count,
        facts_count=facts_count,
        last_ingested_at=document.last_ingested_at,
    )


@router.get(
    "/{doc_id}/pages/{page_no}",
    response_model=DocumentPageResponse,
    summary="문서 페이지 조회",
)
async def get_document_page(
    doc_id: UUID,
    page_no: int,
    db: AsyncSession = Depends(get_db),
):
    """
    문서의 특정 페이지 정보를 조회합니다.

    - **doc_id**: 문서 ID (필수)
    - **page_no**: 페이지 번호 (1-based, 필수)
    """
    result = await db.execute(
        select(DocumentPage).where(
            DocumentPage.doc_id == doc_id,
            DocumentPage.page_no == page_no,
        )
    )
    page = result.scalar_one_or_none()

    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page {page_no} not found for document {doc_id}",
        )

    return DocumentPageResponse.model_validate(page)


@router.get(
    "/{doc_id}/facts",
    response_model=FactListResponse,
    summary="문서 추출 Facts 조회",
)
async def get_document_facts(
    doc_id: UUID,
    fact_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    문서에서 추출된 Facts 목록을 조회합니다.

    - **doc_id**: 문서 ID (필수)
    - **fact_type**: 팩트 타입 필터 (선택, 예: BIZ_INFO, CAPITAL, SHAREHOLDER)
    """
    # First check if document exists
    doc_result = await db.execute(
        select(Document).where(Document.doc_id == doc_id)
    )
    document = doc_result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {doc_id} not found",
        )

    # Get facts
    query = select(Fact).where(Fact.doc_id == doc_id)

    if fact_type:
        query = query.where(Fact.fact_type == fact_type)

    query = query.order_by(Fact.fact_type, Fact.field_key)

    result = await db.execute(query)
    facts = result.scalars().all()

    return FactListResponse(
        facts=[FactResponse.model_validate(f) for f in facts],
        total=len(facts),
    )


@router.get(
    "/corp/{corp_id}/facts",
    response_model=FactListResponse,
    summary="기업 전체 Facts 조회",
)
async def get_corporation_facts(
    corp_id: str,
    doc_type: Optional[DocType] = None,
    fact_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    기업의 모든 문서에서 추출된 Facts를 조회합니다.

    - **corp_id**: 기업 ID (필수)
    - **doc_type**: 문서 타입 필터 (선택)
    - **fact_type**: 팩트 타입 필터 (선택)
    """
    query = select(Fact).where(Fact.corp_id == corp_id)

    if doc_type:
        query = query.where(Fact.doc_type == doc_type)

    if fact_type:
        query = query.where(Fact.fact_type == fact_type)

    query = query.order_by(Fact.doc_type, Fact.fact_type, Fact.field_key)

    result = await db.execute(query)
    facts = result.scalars().all()

    return FactListResponse(
        facts=[FactResponse.model_validate(f) for f in facts],
        total=len(facts),
    )


# =============================================================================
# Document Upload Endpoints
# =============================================================================

import re

# Valid corp_id pattern: alphanumeric with hyphens (e.g., "8001-3719240")
VALID_CORP_ID_PATTERN = re.compile(r'^[\w-]+$')


def _validate_corp_id(corp_id: str) -> None:
    """Validate corp_id to prevent path traversal attacks"""
    if not VALID_CORP_ID_PATTERN.match(corp_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid corp_id format. Only alphanumeric characters and hyphens allowed.",
        )
    if ".." in corp_id or "/" in corp_id or "\\" in corp_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid corp_id: path traversal characters not allowed.",
        )


def _ensure_storage_directory(corp_id: str) -> Path:
    """Ensure storage directory exists for corporation"""
    _validate_corp_id(corp_id)
    corp_dir = DOCUMENT_STORAGE_PATH / corp_id
    corp_dir.mkdir(parents=True, exist_ok=True)
    return corp_dir


def _compute_file_hash(content: bytes) -> str:
    """Compute SHA256 hash of file content"""
    return hashlib.sha256(content).hexdigest()


def _validate_file(file: UploadFile) -> None:
    """Validate uploaded file"""
    # Check extension
    if file.filename:
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}",
            )


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    summary="문서 업로드",
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    corp_id: str = Form(..., description="기업 ID"),
    doc_type: DocType = Form(..., description="문서 타입"),
    file: UploadFile = File(..., description="문서 파일 (jpg, png, pdf)"),
    db: AsyncSession = Depends(get_db),
):
    """
    문서 파일을 업로드하고 DB에 등록합니다.

    - **corp_id**: 기업 ID (필수)
    - **doc_type**: 문서 타입 (BIZ_REG, REGISTRY, SHAREHOLDERS, AOI, FIN_STATEMENT)
    - **file**: 문서 파일 (jpg, png, pdf, tiff)

    업로드 후 분석을 실행하려면:
    1. POST /api/v1/jobs/analyze/run 으로 분석 트리거
    2. 또는 /upload-and-process 엔드포인트 사용 (즉시 처리)
    """
    # Validate file
    _validate_file(file)

    # Read file content
    content = await file.read()

    # Check file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE / 1024 / 1024}MB",
        )

    # Compute file hash
    file_hash = _compute_file_hash(content)

    # Check for duplicate (same corp_id, doc_type, file_hash)
    existing = await db.execute(
        select(Document).where(
            Document.corp_id == corp_id,
            Document.doc_type == doc_type,
            Document.file_hash == file_hash,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document with same content already exists for this corporation",
        )

    # Ensure storage directory
    corp_dir = _ensure_storage_directory(corp_id)

    # Generate filename
    ext = Path(file.filename).suffix.lower() if file.filename else ".jpg"
    doc_id = uuid4()
    filename = f"{doc_type.value}_{doc_id.hex[:8]}{ext}"
    file_path = corp_dir / filename

    # Save file
    with open(file_path, "wb") as f:
        f.write(content)

    # Create document record
    document = Document(
        doc_id=doc_id,
        corp_id=corp_id,
        doc_type=doc_type,
        storage_provider="FILESYS",
        storage_path=str(file_path),
        file_hash=file_hash,
        page_count=1,  # For now, assume single page
        captured_at=datetime.now(UTC),
        ingest_status=IngestStatus.PENDING,
        created_at=datetime.now(UTC),
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)

    return DocumentUploadResponse(
        doc_id=document.doc_id,
        corp_id=document.corp_id,
        doc_type=document.doc_type,
        file_name=filename,
        file_size=len(content),
        storage_path=str(file_path),
        ingest_status=document.ingest_status,
        message=f"Document uploaded successfully. Run analysis job to extract facts.",
    )


@router.post(
    "/upload-and-process",
    response_model=DocumentUploadWithProcessResponse,
    summary="문서 업로드 및 즉시 처리",
    status_code=status.HTTP_201_CREATED,
)
async def upload_and_process_document(
    corp_id: str = Form(..., description="기업 ID"),
    doc_type: DocType = Form(..., description="문서 타입"),
    file: UploadFile = File(..., description="문서 파일 (jpg, png, pdf)"),
    db: AsyncSession = Depends(get_db),
):
    """
    문서 파일을 업로드하고 즉시 Vision LLM으로 처리합니다.

    - **corp_id**: 기업 ID (필수)
    - **doc_type**: 문서 타입 (BIZ_REG, REGISTRY, SHAREHOLDERS, AOI, FIN_STATEMENT)
    - **file**: 문서 파일 (jpg, png, pdf, tiff)

    이 엔드포인트는 동기적으로 처리하므로 응답까지 시간이 걸릴 수 있습니다 (3-10초).
    대용량 배치 처리는 Job 시스템을 사용하세요.
    """
    # Validate file
    _validate_file(file)

    # Read file content
    content = await file.read()

    # Check file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE / 1024 / 1024}MB",
        )

    # Compute file hash
    file_hash = _compute_file_hash(content)

    # Ensure storage directory
    corp_dir = _ensure_storage_directory(corp_id)

    # Generate filename
    ext = Path(file.filename).suffix.lower() if file.filename else ".jpg"
    doc_id = uuid4()
    filename = f"{doc_type.value}_{doc_id.hex[:8]}{ext}"
    file_path = corp_dir / filename

    # Save file
    with open(file_path, "wb") as f:
        f.write(content)

    # Create document record
    document = Document(
        doc_id=doc_id,
        corp_id=corp_id,
        doc_type=doc_type,
        storage_provider="FILESYS",
        storage_path=str(file_path),
        file_hash=file_hash,
        page_count=1,
        captured_at=datetime.now(UTC),
        ingest_status=IngestStatus.RUNNING,
        created_at=datetime.now(UTC),
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)

    # Process document immediately using DocIngestPipeline
    start_time = time.time()
    facts_extracted = 0
    extracted_facts = []

    try:
        from app.worker.pipelines.doc_ingest import DocIngestPipeline

        pipeline = DocIngestPipeline()

        # Convert to base64 for Vision LLM
        image_base64 = base64.b64encode(content).decode("utf-8")

        # Process single document
        result = pipeline.process_single_document(
            corp_id=corp_id,
            doc_type=doc_type.value,
            image_base64=image_base64,
        )

        facts_extracted = len(result.get("facts", []))

        # Save facts to database (sync operation in async context)
        from app.worker.db import get_sync_db

        with get_sync_db() as sync_db:
            for fact_data in result.get("facts", []):
                from app.models.document import ConfidenceLevel

                # Parse confidence
                confidence_str = fact_data.get("confidence", "MED")
                try:
                    confidence = ConfidenceLevel(confidence_str)
                except ValueError:
                    confidence = ConfidenceLevel.MED

                # Determine value type
                field_value = fact_data.get("field_value")
                field_value_text = None
                field_value_num = None
                field_value_json = None

                if isinstance(field_value, str):
                    field_value_text = field_value
                elif isinstance(field_value, (int, float)):
                    field_value_num = field_value
                elif isinstance(field_value, (dict, list)):
                    field_value_json = field_value
                else:
                    field_value_text = str(field_value) if field_value else None

                fact = Fact(
                    fact_id=uuid4(),
                    corp_id=corp_id,
                    doc_id=doc_id,
                    doc_type=doc_type,
                    fact_type=fact_data.get("fact_type", "UNKNOWN"),
                    field_key=fact_data.get("field_key", "unknown"),
                    field_value_text=field_value_text,
                    field_value_num=field_value_num,
                    field_value_json=field_value_json,
                    confidence=confidence,
                    evidence_snippet=fact_data.get("evidence_snippet", "")[:400],
                    evidence_page_no=fact_data.get("page_no", 1),
                    extracted_by="vision-llm",
                    extracted_at=datetime.now(UTC),
                )
                sync_db.add(fact)

                extracted_facts.append(FactResponse(
                    fact_id=fact.fact_id,
                    corp_id=fact.corp_id,
                    doc_id=fact.doc_id,
                    doc_type=fact.doc_type,
                    fact_type=fact.fact_type,
                    field_key=fact.field_key,
                    field_value_text=fact.field_value_text,
                    field_value_num=float(fact.field_value_num) if fact.field_value_num else None,
                    field_value_json=fact.field_value_json,
                    confidence=fact.confidence,
                    evidence_snippet=fact.evidence_snippet,
                    evidence_page_no=fact.evidence_page_no,
                    extracted_by=fact.extracted_by,
                    extracted_at=fact.extracted_at,
                ))

            sync_db.commit()

        # Update document status
        document.ingest_status = IngestStatus.DONE
        document.last_ingested_at = datetime.now(UTC)
        await db.commit()

        processing_time_ms = int((time.time() - start_time) * 1000)

        return DocumentUploadWithProcessResponse(
            doc_id=document.doc_id,
            corp_id=document.corp_id,
            doc_type=document.doc_type,
            file_name=filename,
            ingest_status=IngestStatus.DONE,
            facts_extracted=facts_extracted,
            facts=extracted_facts,
            processing_time_ms=processing_time_ms,
            message=f"Document processed successfully. Extracted {facts_extracted} facts.",
        )

    except Exception as e:
        # Update document status to failed
        document.ingest_status = IngestStatus.FAILED
        await db.commit()

        processing_time_ms = int((time.time() - start_time) * 1000)

        return DocumentUploadWithProcessResponse(
            doc_id=document.doc_id,
            corp_id=document.corp_id,
            doc_type=document.doc_type,
            file_name=filename,
            ingest_status=IngestStatus.FAILED,
            facts_extracted=0,
            facts=[],
            processing_time_ms=processing_time_ms,
            message=f"Document processing failed: {str(e)}",
        )


@router.delete(
    "/{doc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="문서 삭제",
)
async def delete_document(
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    문서와 관련 데이터(Facts, 파일)를 삭제합니다.

    - **doc_id**: 문서 ID (필수)
    """
    # Get document
    result = await db.execute(
        select(Document).where(Document.doc_id == doc_id)
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {doc_id} not found",
        )

    # Delete file if exists
    if document.storage_path:
        file_path = Path(document.storage_path)
        if file_path.exists():
            file_path.unlink()

    # Delete document (cascade deletes facts)
    await db.delete(document)
    await db.commit()
