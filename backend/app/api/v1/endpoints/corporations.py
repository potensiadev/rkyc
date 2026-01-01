"""
rKYC Corporations API Endpoints
CRUD operations for corporations (PRD 14.1.1)

Endpoints:
- GET    /corporations                       - 기업 목록 (페이지네이션, 필터)
- GET    /corporations/{corp_id}             - 기업 상세
- GET    /corporations/{corp_id}/snapshot    - 최신 Snapshot 조회
- POST   /corporations                       - 기업 등록
- PATCH  /corporations/{corp_id}             - 기업 수정
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.models.corporation import Corporation
from app.models.snapshot import InternalSnapshot, InternalSnapshotLatest
from app.schemas.corporation import (
    CorporationCreate,
    CorporationUpdate,
    CorporationResponse,
    CorporationListResponse,
)
from app.schemas.snapshot import SnapshotResponse

router = APIRouter()


@router.get("", response_model=CorporationListResponse)
async def list_corporations(
    industry_code: Optional[str] = Query(None, description="업종코드 필터"),
    search: Optional[str] = Query(None, description="기업명 검색"),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """기업 목록 조회 (페이지네이션 및 필터 지원)"""

    # Build query
    query = select(Corporation)

    if industry_code:
        query = query.where(Corporation.industry_code == industry_code)

    if search:
        query = query.where(Corporation.corp_name.ilike(f"%{search}%"))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Get items with pagination
    query = query.limit(limit).offset(offset).order_by(Corporation.created_at.desc())
    result = await db.execute(query)
    items = result.scalars().all()

    return CorporationListResponse(total=total, items=items)


@router.get("/{corp_id}", response_model=CorporationResponse)
async def get_corporation(
    corp_id: str,
    db: AsyncSession = Depends(get_db),
):
    """기업 상세 조회"""

    query = select(Corporation).where(Corporation.corp_id == corp_id)
    result = await db.execute(query)
    corporation = result.scalar_one_or_none()

    if not corporation:
        raise HTTPException(status_code=404, detail="Corporation not found")

    return corporation


@router.get("/{corp_id}/snapshot", response_model=SnapshotResponse)
async def get_corporation_snapshot(
    corp_id: str,
    db: AsyncSession = Depends(get_db),
):
    """기업 최신 Snapshot 조회 (PRD 14.2)"""

    # 기업 존재 확인
    corp_query = select(Corporation).where(Corporation.corp_id == corp_id)
    corp_result = await db.execute(corp_query)
    if not corp_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Corporation not found")

    # 최신 Snapshot 포인터 조회
    latest_query = select(InternalSnapshotLatest).where(
        InternalSnapshotLatest.corp_id == corp_id
    )
    latest_result = await db.execute(latest_query)
    latest = latest_result.scalar_one_or_none()

    if not latest:
        raise HTTPException(status_code=404, detail="No snapshot found for this corporation")

    # Snapshot 상세 조회
    snapshot_query = select(InternalSnapshot).where(
        InternalSnapshot.snapshot_id == latest.snapshot_id
    )
    snapshot_result = await db.execute(snapshot_query)
    snapshot = snapshot_result.scalar_one_or_none()

    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot data not found")

    return snapshot


@router.post("", response_model=CorporationResponse, status_code=201)
async def create_corporation(
    corporation_in: CorporationCreate,
    db: AsyncSession = Depends(get_db),
):
    """기업 등록"""

    # Check if corp_id already exists
    query = select(Corporation).where(Corporation.corp_id == corporation_in.corp_id)
    result = await db.execute(query)
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(status_code=400, detail="Corporation ID already exists")

    # Create new corporation
    corporation = Corporation(**corporation_in.model_dump())
    db.add(corporation)
    await db.commit()
    await db.refresh(corporation)

    return corporation


@router.patch("/{corp_id}", response_model=CorporationResponse)
async def update_corporation(
    corp_id: str,
    corporation_in: CorporationUpdate,
    db: AsyncSession = Depends(get_db),
):
    """기업 정보 수정"""

    # Get existing corporation
    query = select(Corporation).where(Corporation.corp_id == corp_id)
    result = await db.execute(query)
    corporation = result.scalar_one_or_none()

    if not corporation:
        raise HTTPException(status_code=404, detail="Corporation not found")

    # Update fields
    update_data = corporation_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(corporation, field, value)

    await db.commit()
    await db.refresh(corporation)

    return corporation
