"""
Admin API Endpoints

PRD v1.2:
- Circuit Breaker 상태 조회 API
- 수동 리셋 API
- P2-2: Profile 재생성 API
- v1.2: LLM Cache 상태 조회 API
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.worker.llm.circuit_breaker import (
    get_circuit_breaker_manager,
    CircuitState,
)
from app.worker.llm.cache import get_llm_cache, CacheOperation
from app.core.database import get_db

router = APIRouter(prefix="/admin", tags=["admin"])


# ============================================================================
# Schemas
# ============================================================================


class CircuitStatusResponse(BaseModel):
    """Circuit Breaker 상태 응답"""
    provider: str
    state: str
    failure_count: int
    success_count: int
    last_failure_at: Optional[str]
    last_success_at: Optional[str]
    opened_at: Optional[str]
    cooldown_remaining: int
    config: dict


class AllCircuitStatusResponse(BaseModel):
    """전체 Circuit Breaker 상태 응답"""
    providers: dict[str, CircuitStatusResponse]


class CircuitResetRequest(BaseModel):
    """Circuit Breaker 리셋 요청"""
    provider: Optional[str] = None  # None이면 전체 리셋


class CircuitResetResponse(BaseModel):
    """Circuit Breaker 리셋 응답"""
    success: bool
    message: str
    reset_providers: list[str]


# ============================================================================
# Endpoints
# ============================================================================


@router.get(
    "/circuit-breaker/status",
    response_model=AllCircuitStatusResponse,
    summary="전체 Circuit Breaker 상태 조회",
    description="모든 LLM Provider의 Circuit Breaker 상태를 조회합니다.",
)
async def get_all_circuit_status():
    """
    전체 Circuit Breaker 상태 조회

    Returns:
        AllCircuitStatusResponse: 모든 provider의 상태
    """
    manager = get_circuit_breaker_manager()
    all_status = manager.get_all_status()

    providers = {}
    for provider, status in all_status.items():
        providers[provider] = CircuitStatusResponse(
            provider=status.provider,
            state=status.state.value,
            failure_count=status.failure_count,
            success_count=status.success_count,
            last_failure_at=status.last_failure_at,
            last_success_at=status.last_success_at,
            opened_at=status.opened_at,
            cooldown_remaining=status.cooldown_remaining,
            config=status.config,
        )

    return AllCircuitStatusResponse(providers=providers)


@router.get(
    "/circuit-breaker/status/{provider}",
    response_model=CircuitStatusResponse,
    summary="특정 Provider Circuit Breaker 상태 조회",
    description="특정 LLM Provider의 Circuit Breaker 상태를 조회합니다.",
)
async def get_circuit_status(provider: str):
    """
    특정 Provider Circuit Breaker 상태 조회

    Args:
        provider: Provider 이름 (perplexity, gemini, claude)

    Returns:
        CircuitStatusResponse: Provider 상태
    """
    manager = get_circuit_breaker_manager()
    status = manager.get_status(provider)

    return CircuitStatusResponse(
        provider=status.provider,
        state=status.state.value,
        failure_count=status.failure_count,
        success_count=status.success_count,
        last_failure_at=status.last_failure_at,
        last_success_at=status.last_success_at,
        opened_at=status.opened_at,
        cooldown_remaining=status.cooldown_remaining,
        config=status.config,
    )


@router.post(
    "/circuit-breaker/reset",
    response_model=CircuitResetResponse,
    summary="Circuit Breaker 리셋",
    description="Circuit Breaker를 수동으로 리셋합니다. provider를 지정하지 않으면 전체 리셋.",
)
async def reset_circuit_breaker(request: CircuitResetRequest):
    """
    Circuit Breaker 수동 리셋

    Args:
        request: 리셋 요청 (provider 지정 가능)

    Returns:
        CircuitResetResponse: 리셋 결과
    """
    manager = get_circuit_breaker_manager()

    if request.provider:
        # 특정 provider 리셋
        manager.reset(request.provider)
        return CircuitResetResponse(
            success=True,
            message=f"Circuit breaker for {request.provider} has been reset",
            reset_providers=[request.provider],
        )
    else:
        # 전체 리셋
        all_status = manager.get_all_status()
        manager.reset_all()
        return CircuitResetResponse(
            success=True,
            message="All circuit breakers have been reset",
            reset_providers=list(all_status.keys()),
        )


@router.get(
    "/test/perplexity",
    summary="Perplexity API 테스트",
    description="Perplexity API 연결을 직접 테스트합니다.",
)
async def test_perplexity():
    """Perplexity API 직접 테스트"""
    import httpx
    from app.core.config import settings

    api_key = settings.PERPLEXITY_API_KEY
    if not api_key:
        return {"success": False, "error": "PERPLEXITY_API_KEY not configured"}

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                "https://api.perplexity.ai/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "sonar-pro",
                    "messages": [{"role": "user", "content": "Say hello in Korean"}],
                    "max_tokens": 50,
                },
            )
            response.raise_for_status()
            data = response.json()
            return {
                "success": True,
                "model": data.get("model"),
                "response_preview": str(data.get("choices", [{}])[0].get("message", {}).get("content", ""))[:100],
                "api_key_prefix": api_key[:10] + "..." if api_key else None,
            }
    except httpx.HTTPStatusError as e:
        return {
            "success": False,
            "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}",
            "api_key_prefix": api_key[:10] + "..." if api_key else None,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "api_key_prefix": api_key[:10] + "..." if api_key else None,
        }


@router.get(
    "/test/gemini",
    summary="Gemini API 테스트",
    description="Gemini API 연결을 직접 테스트합니다.",
)
async def test_gemini():
    """Gemini API 직접 테스트"""
    import httpx
    from app.core.config import settings

    api_key = settings.GOOGLE_API_KEY
    if not api_key:
        return {"success": False, "error": "GOOGLE_API_KEY not configured"}

    try:
        with httpx.Client(timeout=30.0) as client:
            # Test by listing models
            response = client.get(
                f"https://generativelanguage.googleapis.com/v1/models?key={api_key}"
            )
            response.raise_for_status()
            data = response.json()
            models = [m.get("name") for m in data.get("models", [])[:5]]
            return {
                "success": True,
                "models_available": models,
                "api_key_prefix": api_key[:10] + "..." if api_key else None,
            }
    except httpx.HTTPStatusError as e:
        return {
            "success": False,
            "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}",
            "api_key_prefix": api_key[:10] + "..." if api_key else None,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "api_key_prefix": api_key[:10] + "..." if api_key else None,
        }


@router.get(
    "/health/llm",
    summary="LLM Provider 건강 상태",
    description="모든 LLM Provider의 건강 상태를 요약합니다.",
)
async def get_llm_health():
    """
    LLM Provider 건강 상태 요약

    Returns:
        dict: 건강 상태 요약
    """
    manager = get_circuit_breaker_manager()
    all_status = manager.get_all_status()

    healthy = []
    degraded = []
    unavailable = []

    for provider, status in all_status.items():
        if status.state == CircuitState.CLOSED:
            healthy.append(provider)
        elif status.state == CircuitState.HALF_OPEN:
            degraded.append(provider)
        else:  # OPEN
            unavailable.append(provider)

    total = len(all_status)
    healthy_count = len(healthy)

    return {
        "status": "healthy" if healthy_count == total else ("degraded" if healthy_count > 0 else "unhealthy"),
        "summary": {
            "total_providers": total,
            "healthy": healthy_count,
            "degraded": len(degraded),
            "unavailable": len(unavailable),
        },
        "providers": {
            "healthy": healthy,
            "degraded": degraded,
            "unavailable": unavailable,
        },
    }


# ============================================================================
# P2-2: Profile Provenance Regeneration API
# ============================================================================


class ProfileRegenerateRequest(BaseModel):
    """프로파일 재생성 요청"""
    corp_id: Optional[str] = None  # None이면 모든 NULL provenance 대상


class ProfileRegenerateResponse(BaseModel):
    """프로파일 재생성 응답"""
    success: bool
    message: str
    affected_count: int
    corp_ids: list[str]


class ProfileProvenanceStatsResponse(BaseModel):
    """프로파일 Provenance 통계 응답"""
    total_profiles: int
    with_provenance: int
    without_provenance: int
    expired: int
    null_provenance_rate: float


@router.get(
    "/profiles/provenance-stats",
    response_model=ProfileProvenanceStatsResponse,
    summary="프로파일 Provenance 통계",
    description="전체 프로파일의 field_provenance 상태를 집계합니다.",
)
async def get_provenance_stats(db: AsyncSession = Depends(get_db)):
    """
    프로파일 Provenance 통계 조회

    Returns:
        ProfileProvenanceStatsResponse: Provenance 통계
    """
    query = text("""
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE field_provenance IS NOT NULL AND field_provenance != '{}'::jsonb) as with_provenance,
            COUNT(*) FILTER (WHERE field_provenance IS NULL OR field_provenance = '{}'::jsonb) as without_provenance,
            COUNT(*) FILTER (WHERE expires_at < NOW()) as expired
        FROM rkyc_corp_profile
    """)

    result = await db.execute(query)
    row = result.fetchone()

    total = row.total or 0
    without_provenance = row.without_provenance or 0
    null_rate = (without_provenance / total * 100) if total > 0 else 0

    return ProfileProvenanceStatsResponse(
        total_profiles=total,
        with_provenance=row.with_provenance or 0,
        without_provenance=without_provenance,
        expired=row.expired or 0,
        null_provenance_rate=round(null_rate, 2),
    )


@router.post(
    "/profiles/regenerate-provenance",
    response_model=ProfileRegenerateResponse,
    summary="프로파일 Provenance 재생성 트리거",
    description="NULL/빈 field_provenance를 가진 프로파일의 expires_at을 과거로 설정하여 재생성을 트리거합니다.",
)
async def regenerate_provenance(
    request: ProfileRegenerateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    프로파일 Provenance 재생성 트리거

    Args:
        request: 재생성 요청 (corp_id 지정 가능)

    Returns:
        ProfileRegenerateResponse: 재생성 결과
    """
    if request.corp_id:
        # 특정 기업만
        query = text("""
            UPDATE rkyc_corp_profile
            SET expires_at = NOW() - INTERVAL '1 day', updated_at = NOW()
            WHERE corp_id = :corp_id
            RETURNING corp_id
        """)
        result = await db.execute(query, {"corp_id": request.corp_id})
    else:
        # NULL/빈 provenance 전체
        query = text("""
            UPDATE rkyc_corp_profile
            SET expires_at = NOW() - INTERVAL '1 day', updated_at = NOW()
            WHERE field_provenance IS NULL OR field_provenance = '{}'::jsonb
            RETURNING corp_id
        """)
        result = await db.execute(query)

    rows = result.fetchall()
    await db.commit()

    corp_ids = [row.corp_id for row in rows]

    return ProfileRegenerateResponse(
        success=True,
        message=f"Marked {len(corp_ids)} profiles for regeneration",
        affected_count=len(corp_ids),
        corp_ids=corp_ids[:100],  # 최대 100개만 반환
    )


@router.get(
    "/profiles/null-provenance",
    summary="NULL Provenance 프로파일 목록",
    description="field_provenance가 NULL이거나 빈 프로파일 목록을 조회합니다.",
)
async def list_null_provenance_profiles(
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """
    NULL Provenance 프로파일 목록 조회

    Args:
        limit: 조회 개수 (기본 50, 최대 200)

    Returns:
        dict: 프로파일 목록
    """
    query = text("""
        SELECT corp_id, profile_confidence, is_fallback, expires_at, updated_at
        FROM rkyc_corp_profile
        WHERE field_provenance IS NULL OR field_provenance = '{}'::jsonb
        ORDER BY updated_at DESC
        LIMIT :limit
    """)

    result = await db.execute(query, {"limit": limit})
    rows = result.fetchall()

    profiles = [
        {
            "corp_id": row.corp_id,
            "profile_confidence": row.profile_confidence,
            "is_fallback": row.is_fallback,
            "expires_at": row.expires_at.isoformat() if row.expires_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }
        for row in rows
    ]

    return {
        "count": len(profiles),
        "profiles": profiles,
    }


# ============================================================================
# v1.2: LLM Cache Status API
# ============================================================================


class CacheStatsResponse(BaseModel):
    """LLM Cache 통계 응답"""
    memory: dict[str, int]
    redis_available: bool
    redis: Optional[dict[str, int]] = None
    redis_error: Optional[str] = None


class CacheInvalidateRequest(BaseModel):
    """Cache 무효화 요청"""
    operation: Optional[str] = None  # None이면 전체 무효화
    pattern: str = "*"


class CacheInvalidateResponse(BaseModel):
    """Cache 무효화 응답"""
    success: bool
    message: str
    invalidated_count: int


@router.get(
    "/cache/status",
    response_model=CacheStatsResponse,
    summary="LLM Cache 상태 조회",
    description="Memory 및 Redis LLM Cache의 현재 상태를 조회합니다.",
)
async def get_cache_status():
    """
    LLM Cache 상태 조회

    Returns:
        CacheStatsResponse: 캐시 통계
    """
    cache = get_llm_cache()
    stats = await cache.get_stats()

    return CacheStatsResponse(
        memory=stats.get("memory", {}),
        redis_available=stats.get("redis_available", False),
        redis=stats.get("redis"),
        redis_error=stats.get("redis_error"),
    )


@router.post(
    "/cache/invalidate",
    response_model=CacheInvalidateResponse,
    summary="LLM Cache 무효화",
    description="LLM Cache를 무효화합니다. operation을 지정하면 해당 타입만 무효화합니다.",
)
async def invalidate_cache(request: CacheInvalidateRequest):
    """
    LLM Cache 무효화

    Args:
        request: 무효화 요청 (operation, pattern)

    Returns:
        CacheInvalidateResponse: 무효화 결과
    """
    cache = get_llm_cache()

    operation = None
    if request.operation:
        try:
            operation = CacheOperation(request.operation)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid operation: {request.operation}. Valid values: {[op.value for op in CacheOperation]}"
            )

    count = await cache.invalidate_by_pattern(
        operation=operation,
        pattern_suffix=request.pattern,
    )

    return CacheInvalidateResponse(
        success=True,
        message=f"Invalidated {count} cache entries",
        invalidated_count=count,
    )


@router.get(
    "/cache/operations",
    summary="Cache Operation 목록",
    description="사용 가능한 Cache Operation 타입 목록을 조회합니다.",
)
async def list_cache_operations():
    """
    Cache Operation 타입 목록 조회

    Returns:
        dict: Operation 목록과 TTL 설정
    """
    from app.worker.llm.cache import CacheConfig

    config = CacheConfig()
    operations = []

    for op in CacheOperation:
        operations.append({
            "name": op.value,
            "ttl_seconds": config.get_ttl(op),
            "ttl_human": _format_ttl(config.get_ttl(op)),
        })

    return {
        "operations": operations,
        "memory_cache_size": config.MEMORY_CACHE_SIZE,
        "redis_key_prefix": config.REDIS_KEY_PREFIX,
    }


def _format_ttl(seconds: int) -> str:
    """TTL을 사람이 읽기 쉬운 형식으로 변환"""
    if seconds >= 86400:
        days = seconds // 86400
        return f"{days}d"
    elif seconds >= 3600:
        hours = seconds // 3600
        return f"{hours}h"
    elif seconds >= 60:
        minutes = seconds // 60
        return f"{minutes}m"
    else:
        return f"{seconds}s"


# ============================================================================
# Multi-Search Provider Status API (Perplexity 의존도 완화)
# ============================================================================


class SearchProviderStatusResponse(BaseModel):
    """검색 Provider 상태 응답"""
    provider: str
    available: bool
    circuit_state: str
    failure_count: int
    api_key_configured: bool


class AllSearchProvidersStatusResponse(BaseModel):
    """전체 검색 Provider 상태 응답"""
    providers: dict[str, SearchProviderStatusResponse]
    available_count: int
    total_count: int
    fallback_ready: bool


@router.get(
    "/search-providers/status",
    response_model=AllSearchProvidersStatusResponse,
    summary="검색 Provider 상태 조회",
    description="모든 검색 Provider(Perplexity, Tavily, Brave, Gemini)의 상태를 조회합니다.",
)
async def get_search_providers_status_endpoint():
    """
    전체 검색 Provider 상태 조회

    Perplexity 외에 대안 Provider(Tavily, Brave Search, Gemini Grounding)의
    사용 가능 여부를 확인합니다.

    Returns:
        AllSearchProvidersStatusResponse: 모든 provider의 상태
    """
    from app.worker.llm.search_providers import get_search_providers_status

    status_dict = get_search_providers_status()

    providers = {}
    available_count = 0

    for provider_name, status in status_dict.items():
        is_available = status["available"]
        if is_available:
            available_count += 1

        providers[provider_name] = SearchProviderStatusResponse(
            provider=provider_name,
            available=is_available,
            circuit_state=status["circuit_state"],
            failure_count=status["failure_count"],
            api_key_configured=is_available,
        )

    total_count = len(providers)
    # Perplexity 외에 1개 이상 대안이 있으면 fallback_ready
    perplexity_available = providers.get("perplexity", SearchProviderStatusResponse(
        provider="perplexity", available=False, circuit_state="unknown", failure_count=0, api_key_configured=False
    )).available
    fallback_ready = (available_count > 1) or (not perplexity_available and available_count >= 1)

    return AllSearchProvidersStatusResponse(
        providers=providers,
        available_count=available_count,
        total_count=total_count,
        fallback_ready=fallback_ready,
    )


@router.get(
    "/search-providers/health",
    summary="검색 Provider 건강 상태 요약",
    description="검색 Provider의 건강 상태를 요약하고 권장 사항을 제공합니다.",
)
async def get_search_providers_health():
    """
    검색 Provider 건강 상태 요약

    Perplexity 의존도와 Fallback 준비 상태를 분석합니다.

    Returns:
        dict: 건강 상태 요약 및 권장 사항
    """
    from app.worker.llm.search_providers import get_search_providers_status
    from app.core.config import settings

    status_dict = get_search_providers_status()

    # 분석
    perplexity_status = status_dict.get("perplexity", {})
    tavily_status = status_dict.get("tavily", {})
    brave_status = status_dict.get("brave", {})
    gemini_status = status_dict.get("gemini_grounding", {})

    available_providers = [p for p, s in status_dict.items() if s["available"]]
    unavailable_providers = [p for p, s in status_dict.items() if not s["available"]]

    # 위험도 분석
    risk_level = "low"
    recommendations = []

    if len(available_providers) == 0:
        risk_level = "critical"
        recommendations.append("⚠️ 모든 검색 Provider가 사용 불가능합니다. API 키를 확인하세요.")
    elif len(available_providers) == 1 and "perplexity" in available_providers:
        risk_level = "high"
        recommendations.append("⚠️ Perplexity만 사용 가능합니다. 장애 시 검색 기능이 중단됩니다.")
        recommendations.append("→ TAVILY_API_KEY 또는 BRAVE_SEARCH_API_KEY 설정을 권장합니다.")
    elif "perplexity" not in available_providers:
        risk_level = "medium"
        recommendations.append("⚠️ Primary Provider(Perplexity)가 사용 불가능합니다.")
        recommendations.append(f"→ 현재 Fallback Provider({', '.join(available_providers)})로 운영 중입니다.")
    elif len(available_providers) >= 2:
        risk_level = "low"
        recommendations.append("✅ 다중 검색 Provider가 구성되어 있습니다. Fallback 준비 완료.")

    # Circuit Breaker 상태 경고
    for provider, status in status_dict.items():
        if status["circuit_state"] == "open":
            recommendations.append(f"⚠️ {provider}의 Circuit Breaker가 OPEN 상태입니다.")

    return {
        "risk_level": risk_level,
        "summary": {
            "available_providers": available_providers,
            "unavailable_providers": unavailable_providers,
            "total": len(status_dict),
            "available": len(available_providers),
        },
        "perplexity_dependency": {
            "is_sole_provider": len(available_providers) == 1 and "perplexity" in available_providers,
            "has_fallback": len(available_providers) > 1 or "perplexity" not in available_providers,
        },
        "recommendations": recommendations,
        "config_hint": {
            "TAVILY_API_KEY": "설정됨" if settings.TAVILY_API_KEY else "미설정",
            "BRAVE_SEARCH_API_KEY": "설정됨" if settings.BRAVE_SEARCH_API_KEY else "미설정",
            "PERPLEXITY_API_KEY": "설정됨" if settings.PERPLEXITY_API_KEY else "미설정",
            "GOOGLE_API_KEY": "설정됨" if settings.GOOGLE_API_KEY else "미설정",
        },
    }
