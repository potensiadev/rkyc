"""
Corp Profile API Endpoints
PRD: Corp Profiling Pipeline for ENVIRONMENT Signal Enhancement

Endpoints:
- GET /corporations/{corp_id}/profile - Get corp profile
- POST /corporations/{corp_id}/profile/refresh - Force refresh profile
"""

import logging
from datetime import datetime
from typing import Any, Optional
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
    ExecutiveSchema,
    FinancialSnapshotSchema,
    CompetitorSchema,
    MacroFactorSchema,
    SupplyChainSchema,
    OverseasBusinessSchema,
    OverseasSubsidiarySchema,
    ShareholderSchema,
    ConsensusMetadataSchema,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# Helper Functions (PRD Bug Fixes)
# ============================================================================


def _parse_datetime_safely(dt_string: str | None) -> datetime | None:
    """
    datetime 파싱 ("Z" suffix 지원) - P1-3 Fix

    Python 3.10 이하에서는 fromisoformat()이 "Z" suffix를 지원하지 않음.
    """
    if not dt_string:
        return None
    try:
        # "Z"를 "+00:00"으로 치환 (Python 3.10 호환)
        if isinstance(dt_string, str) and dt_string.endswith("Z"):
            dt_string = dt_string[:-1] + "+00:00"
        return datetime.fromisoformat(dt_string)
    except (ValueError, TypeError):
        return None


def _normalize_single_source_risk(value: Any) -> list[str]:
    """
    single_source_risk 타입 정규화 - P0-1 Fix

    LLM이 boolean, string, list 등 다양한 타입으로 반환할 수 있음.
    """
    if value is None:
        return []
    if isinstance(value, bool):
        return ["단일 조달처 위험 있음"] if value else []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [str(item) for item in value if item]
    return []


def _parse_supply_chain(data: dict | None) -> SupplyChainSchema:
    """Parse supply_chain JSONB to schema."""
    if not data:
        return SupplyChainSchema()
    return SupplyChainSchema(
        key_suppliers=data.get("key_suppliers", []),
        supplier_countries=data.get("supplier_countries", {}),
        # P0-1 Fix: 다양한 타입을 list[str]로 정규화
        single_source_risk=_normalize_single_source_risk(data.get("single_source_risk")),
        material_import_ratio_pct=data.get("material_import_ratio_pct"),
    )


def _parse_overseas_business(data: dict | None) -> OverseasBusinessSchema:
    """Parse overseas_business JSONB to schema."""
    if not data:
        return OverseasBusinessSchema()
    subsidiaries = [
        OverseasSubsidiarySchema(
            name=s.get("name", ""),
            country=s.get("country", ""),
            business_type=s.get("business_type"),
            ownership_pct=s.get("ownership_pct"),
        )
        for s in data.get("subsidiaries", [])
    ]
    return OverseasBusinessSchema(
        subsidiaries=subsidiaries,
        manufacturing_countries=data.get("manufacturing_countries", []),
    )


def _parse_consensus_metadata(data: dict | None) -> ConsensusMetadataSchema:
    """Parse consensus_metadata JSONB to schema."""
    if not data:
        return ConsensusMetadataSchema()
    return ConsensusMetadataSchema(
        # P1-3 Fix: "Z" suffix 지원
        consensus_at=_parse_datetime_safely(data.get("consensus_at")),
        perplexity_success=data.get("perplexity_success", False),
        gemini_success=data.get("gemini_success", False),
        claude_success=data.get("claude_success", False),
        total_fields=data.get("total_fields", 0),
        matched_fields=data.get("matched_fields", 0),
        discrepancy_fields=data.get("discrepancy_fields", 0),
        enriched_fields=data.get("enriched_fields", 0),
        overall_confidence=data.get("overall_confidence", "LOW"),
        fallback_layer=data.get("fallback_layer", 0),
        retry_count=data.get("retry_count", 0),
        error_messages=data.get("error_messages", []),
    )


@router.get(
    "/corporations/{corp_id}/profile",
    response_model=CorpProfileResponse,
    summary="기업 프로파일 조회",
    description="""
    기업의 비즈니스 프로파일을 조회합니다. (PRD v1.2)

    - 캐시된 프로파일이 있고 TTL 내이면 캐시 반환
    - TTL 만료 또는 없으면 is_expired=true 반환

    PRD v1.2 확장 필드:
    - supply_chain: 공급망 정보 (key_suppliers, supplier_countries, single_source_risk)
    - overseas_business: 해외 사업 (subsidiaries, manufacturing_countries)
    - consensus_metadata: Consensus 처리 메타데이터

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
    # P1-2 Fix: expires_at NULL 처리
    query = text("""
        SELECT
            profile_id, corp_id, business_summary, revenue_krw, export_ratio_pct,
            ceo_name, employee_count, founded_year, headquarters, executives,
            industry_overview, business_model, financial_history,
            country_exposure, key_materials, key_customers, overseas_operations,
            competitors, macro_factors, supply_chain, overseas_business, shareholders,
            consensus_metadata, profile_confidence, field_confidences, source_urls,
            is_fallback, search_failed, validation_warnings, status,
            fetched_at, expires_at,
            CASE
                WHEN expires_at IS NULL THEN false
                WHEN expires_at < NOW() THEN true
                ELSE false
            END as is_expired
        FROM rkyc_corp_profile
        WHERE corp_id = :corp_id
        LIMIT 1
    """)

    result = await db.execute(query, {"corp_id": corp_id})
    row = result.fetchone()

    if not row:
        # P2-3 Fix: error_code 필드 추가하여 Frontend에서 에러 분기 가능
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "PROFILE_NOT_FOUND",
                "message": "프로필이 아직 생성되지 않았습니다.",
                "action": "정보 갱신 버튼을 클릭하여 프로필을 생성해 주세요.",
                "corp_id": corp_id,
            },
        )

    # Parse JSONB fields to schemas
    executives = [ExecutiveSchema(**e) for e in (row.executives or [])]
    financial_history = [FinancialSnapshotSchema(**f) for f in (row.financial_history or [])]
    competitors = [CompetitorSchema(**c) for c in (row.competitors or [])]
    macro_factors = [MacroFactorSchema(**m) for m in (row.macro_factors or [])]
    shareholders = [ShareholderSchema(**s) for s in (row.shareholders or [])]
    supply_chain = _parse_supply_chain(row.supply_chain)
    overseas_business = _parse_overseas_business(row.overseas_business)
    consensus_metadata = _parse_consensus_metadata(row.consensus_metadata)

    return CorpProfileResponse(
        profile_id=row.profile_id,
        corp_id=row.corp_id,
        business_summary=row.business_summary,
        ceo_name=row.ceo_name,
        employee_count=row.employee_count,
        founded_year=row.founded_year,
        headquarters=row.headquarters,
        executives=executives,
        industry_overview=row.industry_overview,
        business_model=row.business_model,
        revenue_krw=row.revenue_krw,
        export_ratio_pct=row.export_ratio_pct,
        financial_history=financial_history,
        country_exposure=row.country_exposure or {},
        key_materials=list(row.key_materials or []),
        key_customers=list(row.key_customers or []),
        overseas_operations=list(row.overseas_operations or []),
        competitors=competitors,
        macro_factors=macro_factors,
        supply_chain=supply_chain,
        overseas_business=overseas_business,
        shareholders=shareholders,
        consensus_metadata=consensus_metadata,
        profile_confidence=ConfidenceLevelEnum(row.profile_confidence or "LOW"),
        field_confidences=row.field_confidences or {},
        source_urls=list(row.source_urls or []),
        is_fallback=row.is_fallback or False,
        search_failed=row.search_failed or False,
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
    # P1-2 Fix: expires_at NULL 처리
    query = text("""
        SELECT *,
            CASE
                WHEN expires_at IS NULL THEN false
                WHEN expires_at < NOW() THEN true
                ELSE false
            END as is_expired
        FROM rkyc_corp_profile
        WHERE corp_id = :corp_id
        LIMIT 1
    """)

    result = await db.execute(query, {"corp_id": corp_id})
    row = result.fetchone()

    if not row:
        # P2-3 Fix: error_code 필드 추가
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "PROFILE_NOT_FOUND",
                "message": "프로필이 아직 생성되지 않았습니다.",
                "action": "정보 갱신 버튼을 클릭하여 프로필을 생성해 주세요.",
                "corp_id": corp_id,
            },
        )

    # Parse JSONB fields to schemas
    executives = [ExecutiveSchema(**e) for e in (row.executives or [])]
    financial_history = [FinancialSnapshotSchema(**f) for f in (row.financial_history or [])]
    competitors = [CompetitorSchema(**c) for c in (row.competitors or [])]
    macro_factors = [MacroFactorSchema(**m) for m in (row.macro_factors or [])]
    shareholders = [ShareholderSchema(**s) for s in (row.shareholders or [])]
    supply_chain = _parse_supply_chain(row.supply_chain)
    overseas_business = _parse_overseas_business(row.overseas_business)
    consensus_metadata = _parse_consensus_metadata(row.consensus_metadata)

    # Parse field_provenance into response schema
    field_provenance = {}
    raw_provenance = row.field_provenance or {}
    for field_name, prov in raw_provenance.items():
        field_provenance[field_name] = FieldProvenanceResponse(
            source_url=prov.get("source_url"),
            excerpt=prov.get("excerpt"),
            confidence=ConfidenceLevelEnum(prov.get("confidence", "LOW")),
            # P1-3 Fix: "Z" suffix 지원
            extraction_date=_parse_datetime_safely(prov.get("extraction_date")),
        )

    return CorpProfileDetailResponse(
        profile_id=row.profile_id,
        corp_id=row.corp_id,
        business_summary=row.business_summary,
        ceo_name=row.ceo_name,
        employee_count=row.employee_count,
        founded_year=row.founded_year,
        headquarters=row.headquarters,
        executives=executives,
        industry_overview=row.industry_overview,
        business_model=row.business_model,
        revenue_krw=row.revenue_krw,
        export_ratio_pct=row.export_ratio_pct,
        financial_history=financial_history,
        country_exposure=row.country_exposure or {},
        key_materials=list(row.key_materials or []),
        key_customers=list(row.key_customers or []),
        overseas_operations=list(row.overseas_operations or []),
        competitors=competitors,
        macro_factors=macro_factors,
        supply_chain=supply_chain,
        overseas_business=overseas_business,
        shareholders=shareholders,
        consensus_metadata=consensus_metadata,
        profile_confidence=ConfidenceLevelEnum(row.profile_confidence or "LOW"),
        field_confidences=row.field_confidences or {},
        source_urls=list(row.source_urls or []),
        is_fallback=row.is_fallback or False,
        search_failed=row.search_failed or False,
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
    """Trigger profile refresh by creating an analysis job."""
    from app.models.job import Job, JobType, JobStatus

    # Verify corporation exists
    corp_query = text("SELECT corp_id FROM corp WHERE corp_id = :corp_id")
    corp_result = await db.execute(corp_query, {"corp_id": corp_id})
    if not corp_result.fetchone():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Corporation not found: {corp_id}",
        )

    # Mark existing profile as expired if force=true
    if request.force:
        update_query = text("""
            UPDATE rkyc_corp_profile
            SET expires_at = NOW() - INTERVAL '1 second',
                updated_at = NOW()
            WHERE corp_id = :corp_id
        """)
        await db.execute(update_query, {"corp_id": corp_id})

    # Create analysis Job to trigger PROFILING pipeline
    new_job = Job(
        job_type=JobType.ANALYZE,
        corp_id=corp_id,
        status=JobStatus.QUEUED,
    )
    db.add(new_job)
    await db.commit()
    await db.refresh(new_job)

    # Dispatch Celery task with skip_cache=True for force refresh
    celery_dispatch_failed = False
    celery_error_message = None
    try:
        from app.worker.tasks.analysis import run_analysis_pipeline
        # force=True일 때 skip_cache=True로 전달하여 캐시 무시
        task = run_analysis_pipeline.delay(str(new_job.job_id), corp_id, skip_cache=request.force)
        logger.info(f"Profile refresh: Celery task dispatched for job_id={new_job.job_id}, corp_id={corp_id}, skip_cache={request.force}")
    except Exception as e:
        celery_dispatch_failed = True
        celery_error_message = str(e)
        logger.error(f"Profile refresh: Celery dispatch failed - {e}")

        # Update job status to FAILED
        new_job.status = JobStatus.FAILED
        new_job.error_code = "CELERY_DISPATCH_FAILED"
        new_job.error_message = f"Worker 연결 실패: {str(e)[:200]}"
        await db.commit()

    if celery_dispatch_failed:
        return {
            "message": f"프로필 갱신 작업 생성 실패: {celery_error_message[:100]}",
            "corp_id": corp_id,
            "job_id": str(new_job.job_id),
            "status": "FAILED",
            "error": "Worker에 연결할 수 없습니다. 관리자에게 문의하세요.",
        }

    return {
        "message": f"프로필 갱신 작업이 시작되었습니다.",
        "corp_id": corp_id,
        "job_id": str(new_job.job_id),
        "status": "QUEUED",
        "note": "작업 완료 후 프로필이 자동으로 갱신됩니다.",
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
