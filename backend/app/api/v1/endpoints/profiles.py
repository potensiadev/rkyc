"""
Corp Profile API Endpoints
PRD: Corp Profiling Pipeline for ENVIRONMENT Signal Enhancement

Endpoints:
- GET /corporations/{corp_id}/profile - Get corp profile
- POST /corporations/{corp_id}/profile/refresh - Force refresh profile
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.profile import (
    CorpProfileResponse,
    CorpProfileDetailResponse,
    ProfileRefreshRequest,
    ProfileQuerySelectionResponse,
    FieldProvenanceResponse,
    ConfidenceLevelEnum,
    ProfileStatusEnum,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/corporations/{corp_id}/profile",
    response_model=CorpProfileResponse,
    summary="기업 프로파일 조회",
    description="""
    기업의 비즈니스 프로파일을 조회합니다.

    - 캐시된 프로파일이 있고 TTL 내이면 캐시 반환
    - TTL 만료 또는 없으면 is_expired=true 반환

    Anti-Hallucination 정보:
    - profile_confidence: 전체 신뢰도
    - field_confidences: 필드별 신뢰도
    - source_urls: 출처 URL 목록
    - is_fallback: 업종 기본 프로파일 여부
    """,
)
async def get_corp_profile(
    corp_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get corp profile by corp_id."""
    query = text("""
        SELECT
            profile_id, corp_id, business_summary, revenue_krw, export_ratio_pct,
            country_exposure, key_materials, key_customers, overseas_operations,
            profile_confidence, field_confidences, source_urls,
            is_fallback, search_failed, validation_warnings, status,
            fetched_at, expires_at,
            CASE WHEN expires_at < NOW() THEN true ELSE false END as is_expired
        FROM rkyc_corp_profile
        WHERE corp_id = :corp_id
        LIMIT 1
    """)

    result = await db.execute(query, {"corp_id": corp_id})
    row = result.fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile not found for corp_id: {corp_id}. Run analysis to generate profile.",
        )

    return CorpProfileResponse(
        profile_id=row.profile_id,
        corp_id=row.corp_id,
        business_summary=row.business_summary,
        revenue_krw=row.revenue_krw,
        export_ratio_pct=row.export_ratio_pct,
        country_exposure=row.country_exposure or {},
        key_materials=list(row.key_materials or []),
        key_customers=list(row.key_customers or []),
        overseas_operations=list(row.overseas_operations or []),
        profile_confidence=ConfidenceLevelEnum(row.profile_confidence),
        field_confidences=row.field_confidences or {},
        source_urls=list(row.source_urls or []),
        is_fallback=row.is_fallback,
        search_failed=row.search_failed,
        validation_warnings=list(row.validation_warnings or []),
        status=ProfileStatusEnum(row.status) if row.status else ProfileStatusEnum.ACTIVE,
        fetched_at=row.fetched_at,
        expires_at=row.expires_at,
        is_expired=row.is_expired,
    )


@router.get(
    "/corporations/{corp_id}/profile/detail",
    response_model=CorpProfileDetailResponse,
    summary="기업 프로파일 상세 조회 (Provenance 포함)",
    description="""
    기업의 비즈니스 프로파일 상세 정보를 조회합니다.

    Audit Trail 정보 포함:
    - field_provenance: 필드별 출처 매핑 (source_url, excerpt, confidence)
    - extraction_model: 추출에 사용된 LLM 모델
    - extraction_prompt_version: 프롬프트 버전

    이 정보로 각 필드의 원본 출처를 추적할 수 있습니다.
    """,
)
async def get_corp_profile_detail(
    corp_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get detailed corp profile with provenance."""
    query = text("""
        SELECT *,
            CASE WHEN expires_at < NOW() THEN true ELSE false END as is_expired
        FROM rkyc_corp_profile
        WHERE corp_id = :corp_id
        LIMIT 1
    """)

    result = await db.execute(query, {"corp_id": corp_id})
    row = result.fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile not found for corp_id: {corp_id}",
        )

    # Parse field_provenance into response schema
    field_provenance = {}
    raw_provenance = row.field_provenance or {}
    for field_name, prov in raw_provenance.items():
        field_provenance[field_name] = FieldProvenanceResponse(
            source_url=prov.get("source_url"),
            excerpt=prov.get("excerpt"),
            confidence=ConfidenceLevelEnum(prov.get("confidence", "LOW")),
            extraction_date=datetime.fromisoformat(prov["extraction_date"]) if prov.get("extraction_date") else None,
        )

    return CorpProfileDetailResponse(
        profile_id=row.profile_id,
        corp_id=row.corp_id,
        business_summary=row.business_summary,
        revenue_krw=row.revenue_krw,
        export_ratio_pct=row.export_ratio_pct,
        country_exposure=row.country_exposure or {},
        key_materials=list(row.key_materials or []),
        key_customers=list(row.key_customers or []),
        overseas_operations=list(row.overseas_operations or []),
        profile_confidence=ConfidenceLevelEnum(row.profile_confidence),
        field_confidences=row.field_confidences or {},
        source_urls=list(row.source_urls or []),
        is_fallback=row.is_fallback,
        search_failed=row.search_failed,
        validation_warnings=list(row.validation_warnings or []),
        status=ProfileStatusEnum(row.status) if row.status else ProfileStatusEnum.ACTIVE,
        fetched_at=row.fetched_at,
        expires_at=row.expires_at,
        is_expired=row.is_expired,
        field_provenance=field_provenance,
        extraction_model=row.extraction_model,
        extraction_prompt_version=row.extraction_prompt_version,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.post(
    "/corporations/{corp_id}/profile/refresh",
    response_model=dict,
    summary="프로파일 강제 갱신",
    description="""
    기업 프로파일을 강제로 갱신합니다.

    - TTL과 관계없이 새로 Perplexity 검색 및 LLM 추출 수행
    - 분석 작업(Job)을 통해 백그라운드에서 실행됨
    - 갱신 완료까지 기존 프로파일 유지

    **주의**: API 호출 비용이 발생합니다.
    """,
)
async def refresh_corp_profile(
    corp_id: str,
    request: ProfileRefreshRequest = ProfileRefreshRequest(),
    db: AsyncSession = Depends(get_db),
):
    """Trigger profile refresh."""
    # Verify corporation exists
    corp_query = text("SELECT corp_id FROM corp WHERE corp_id = :corp_id")
    corp_result = await db.execute(corp_query, {"corp_id": corp_id})
    if not corp_result.fetchone():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Corporation not found: {corp_id}",
        )

    # For now, just mark existing profile as expired to trigger refresh on next analysis
    if request.force:
        update_query = text("""
            UPDATE rkyc_corp_profile
            SET expires_at = NOW() - INTERVAL '1 second',
                updated_at = NOW()
            WHERE corp_id = :corp_id
        """)
        await db.execute(update_query, {"corp_id": corp_id})
        await db.commit()

    return {
        "message": f"Profile refresh triggered for corp_id: {corp_id}",
        "corp_id": corp_id,
        "force": request.force,
        "note": "Run analysis job to generate new profile",
    }


@router.get(
    "/corporations/{corp_id}/profile/queries",
    response_model=ProfileQuerySelectionResponse,
    summary="조건부 쿼리 선택 결과 조회",
    description="""
    프로파일 기반 조건부 ENVIRONMENT 쿼리 선택 결과를 조회합니다.

    프로파일 데이터에 따라 활성화되는 쿼리 카테고리:
    - FX_RISK: export_ratio >= 30%
    - GEOPOLITICAL: 중국/미국 노출 또는 해외 법인
    - SUPPLY_CHAIN: 중국 노출 또는 원자재 의존
    - COMMODITY: 원자재 존재
    - CYBER_TECH: 업종 C26, C21
    - 등등...

    각 쿼리별 충족 조건도 함께 반환됩니다.
    """,
)
async def get_profile_query_selection(
    corp_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get conditional query selection based on profile."""
    from app.services.query_selector import EnvironmentQuerySelector

    # Get profile
    query = text("""
        SELECT corp_id, export_ratio_pct, country_exposure, key_materials,
               key_customers, overseas_operations, profile_confidence
        FROM rkyc_corp_profile
        WHERE corp_id = :corp_id
        LIMIT 1
    """)

    result = await db.execute(query, {"corp_id": corp_id})
    row = result.fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile not found for corp_id: {corp_id}",
        )

    # Get industry_code from corp table
    corp_query = text("SELECT industry_code FROM corp WHERE corp_id = :corp_id")
    corp_result = await db.execute(corp_query, {"corp_id": corp_id})
    corp_row = corp_result.fetchone()
    industry_code = corp_row.industry_code if corp_row else ""

    # Build profile dict
    profile = {
        "export_ratio_pct": row.export_ratio_pct,
        "country_exposure": row.country_exposure or {},
        "key_materials": list(row.key_materials or []),
        "key_customers": list(row.key_customers or []),
        "overseas_operations": list(row.overseas_operations or []),
    }

    # Run query selection
    selector = EnvironmentQuerySelector()
    selected, details = selector.select_queries(profile, industry_code)

    # Get all possible queries for skipped list
    all_queries = list(selector.QUERY_CONDITIONS.keys())
    skipped = [q for q in all_queries if q not in selected]

    return ProfileQuerySelectionResponse(
        corp_id=corp_id,
        profile_confidence=ConfidenceLevelEnum(row.profile_confidence),
        selected_queries=selected,
        query_details=details,
        skipped_queries=skipped,
    )
