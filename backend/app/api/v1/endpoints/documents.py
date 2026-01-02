"""
Documents API Endpoints
PRD 16.3 기준 - 문서 관리 및 추출된 Facts 조회
"""

from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
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
)

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


# Note: The ingest endpoint below is for testing/demo purposes.
# In production, document ingestion would be triggered through the Job system.

# @router.post(
#     "/ingest",
#     response_model=DocumentIngestResponse,
#     summary="문서 즉시 처리 (테스트용)",
#     status_code=status.HTTP_202_ACCEPTED,
# )
# async def ingest_document(
#     request: DocumentIngestRequest,
#     db: AsyncSession = Depends(get_db),
# ):
#     """
#     문서 이미지를 즉시 처리하여 Facts를 추출합니다.
#     (테스트/데모용 - 프로덕션에서는 Job 시스템 사용)
#
#     - **corp_id**: 기업 ID
#     - **doc_type**: 문서 타입
#     - **image_base64**: Base64 인코딩된 문서 이미지
#     """
#     # This would call DocIngestPipeline.process_single_document()
#     # Implementation depends on sync vs async execution strategy
#     pass
