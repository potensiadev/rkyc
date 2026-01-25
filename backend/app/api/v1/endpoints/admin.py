"""
Admin API Endpoints

PRD v1.2:
- Circuit Breaker 상태 조회 API
- 수동 리셋 API
- P2-2: Profile 재생성 API

ADR-009 Sprint 1:
- LLM Usage 통계 조회 API

ADR-009 Sprint 3/4:
- Signal Agent Orchestrator 모니터링 API
- Agent Performance 메트릭
- Conflict 통계
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
from app.worker.llm.usage_tracker import get_usage_tracker
from app.worker.pipelines.signal_agents import (
    get_signal_orchestrator,
    reset_signal_orchestrator,
)
from app.worker.pipelines.signal_agents.orchestrator import (
    AgentStatus,
    get_concurrency_limiter,
)
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
# LLM Usage Tracking (ADR-009 Sprint 1)
# ============================================================================


class LLMUsageSummaryResponse(BaseModel):
    """LLM Usage 요약 응답"""
    period_start: str
    period_end: str
    total_calls: int
    total_tokens: int
    total_cost_usd: float
    avg_latency_ms: float
    success_rate: float
    by_provider: dict
    by_agent: dict
    by_stage: dict


class LLMUsageTotalsResponse(BaseModel):
    """LLM Usage 전체 통계 응답"""
    calls: int
    tokens: int
    cost_usd: float
    by_provider: dict
    by_agent: dict


@router.get(
    "/llm-usage/summary",
    response_model=LLMUsageSummaryResponse,
    summary="LLM Usage 통계 요약",
    description="지정된 시간 동안의 LLM 사용 통계를 조회합니다.",
)
async def get_llm_usage_summary(
    minutes: int = Query(default=60, ge=1, le=1440, description="조회할 기간 (분)")
):
    """
    LLM Usage 통계 요약

    Args:
        minutes: 조회 기간 (분, 기본 60분, 최대 24시간)

    Returns:
        LLMUsageSummaryResponse: 기간 내 사용 통계
    """
    tracker = get_usage_tracker()
    summary = tracker.get_summary(last_n_minutes=minutes)

    return LLMUsageSummaryResponse(
        period_start=summary.period_start,
        period_end=summary.period_end,
        total_calls=summary.total_calls,
        total_tokens=summary.total_tokens,
        total_cost_usd=round(summary.total_cost_usd, 6),
        avg_latency_ms=round(summary.avg_latency_ms, 2),
        success_rate=round(summary.success_rate, 4),
        by_provider=summary.by_provider,
        by_agent=summary.by_agent,
        by_stage=summary.by_stage,
    )


@router.get(
    "/llm-usage/totals",
    response_model=LLMUsageTotalsResponse,
    summary="LLM Usage 전체 통계",
    description="서버 시작 이후 전체 LLM 사용 통계를 조회합니다.",
)
async def get_llm_usage_totals():
    """
    LLM Usage 전체 통계

    Returns:
        LLMUsageTotalsResponse: 전체 사용 통계
    """
    tracker = get_usage_tracker()
    totals = tracker.get_totals()

    return LLMUsageTotalsResponse(
        calls=totals["calls"],
        tokens=totals["tokens"],
        cost_usd=round(totals["cost_usd"], 6),
        by_provider=dict(totals["by_provider"]),
        by_agent=dict(totals["by_agent"]),
    )


@router.post(
    "/llm-usage/reset",
    summary="LLM Usage 통계 리셋",
    description="LLM 사용 통계를 리셋합니다. (테스트용)",
)
async def reset_llm_usage():
    """
    LLM Usage 통계 리셋

    Returns:
        dict: 리셋 결과
    """
    tracker = get_usage_tracker()
    tracker.reset()

    return {
        "success": True,
        "message": "LLM usage statistics have been reset",
    }


# ============================================================================
# Signal Agent Orchestrator Monitoring (ADR-009 Sprint 3/4)
# ============================================================================


class OrchestratorStatusResponse(BaseModel):
    """Orchestrator 상태 응답"""
    is_initialized: bool
    execution_mode: str  # "local" or "distributed"
    agent_count: int
    agents: list[str]
    cross_validation_enabled: bool
    graceful_degradation_enabled: bool


class AgentPerformanceResponse(BaseModel):
    """Agent 성능 메트릭 응답"""
    agent_name: str
    total_executions: int
    success_count: int
    failure_count: int
    timeout_count: int
    avg_execution_time_ms: float
    total_signals_produced: int
    success_rate: float


class ConcurrencyLimiterStatusResponse(BaseModel):
    """Concurrency Limiter 상태 응답"""
    provider: str
    limit: int
    current_permits: int
    waiting_count: int


class ConflictStatisticsResponse(BaseModel):
    """Conflict 통계 응답"""
    total_conflicts_detected: int
    conflicts_by_field: dict[str, int]
    needs_review_count: int
    auto_resolved_count: int


@router.get(
    "/signal-orchestrator/status",
    response_model=OrchestratorStatusResponse,
    summary="Signal Orchestrator 상태 조회",
    description="Signal Agent Orchestrator의 현재 상태를 조회합니다.",
)
async def get_orchestrator_status():
    """
    Signal Agent Orchestrator 상태 조회

    Returns:
        OrchestratorStatusResponse: Orchestrator 상태
    """
    try:
        orchestrator = get_signal_orchestrator()
        return OrchestratorStatusResponse(
            is_initialized=True,
            execution_mode="local",  # ThreadPoolExecutor
            agent_count=len(orchestrator._agents),
            agents=list(orchestrator._agents.keys()),
            cross_validation_enabled=True,
            graceful_degradation_enabled=True,
        )
    except Exception as e:
        return OrchestratorStatusResponse(
            is_initialized=False,
            execution_mode="unknown",
            agent_count=0,
            agents=[],
            cross_validation_enabled=False,
            graceful_degradation_enabled=False,
        )


@router.get(
    "/signal-orchestrator/concurrency",
    summary="Concurrency Limiter 상태 조회",
    description="Provider별 Concurrency Limiter 상태를 조회합니다.",
)
async def get_concurrency_status():
    """
    Concurrency Limiter 상태 조회

    Returns:
        dict: Provider별 concurrency 상태
    """
    limiter = get_concurrency_limiter()

    providers_status = {}
    for provider, semaphore in limiter._semaphores.items():
        limit = limiter._limits.get(provider, 0)
        # BoundedSemaphore doesn't expose current count directly
        # We track it via the limiter's internal state
        providers_status[provider] = {
            "limit": limit,
            "provider": provider,
        }

    return {
        "providers": providers_status,
        "default_limit": limiter._default_limit,
    }


@router.post(
    "/signal-orchestrator/reset",
    summary="Signal Orchestrator 리셋",
    description="Signal Agent Orchestrator를 리셋합니다.",
)
async def reset_orchestrator():
    """
    Signal Agent Orchestrator 리셋

    Returns:
        dict: 리셋 결과
    """
    reset_signal_orchestrator()

    return {
        "success": True,
        "message": "Signal Agent Orchestrator has been reset",
    }


@router.get(
    "/signal-agents/list",
    summary="등록된 Signal Agent 목록",
    description="Orchestrator에 등록된 모든 Signal Agent 목록을 조회합니다.",
)
async def list_signal_agents():
    """
    등록된 Signal Agent 목록

    Returns:
        dict: Agent 목록 및 정보
    """
    orchestrator = get_signal_orchestrator()

    agents_info = []
    for name, agent in orchestrator._agents.items():
        # P0-6 Fix: Use correct attribute names (SIGNAL_TYPE, ALLOWED_EVENT_TYPES)
        agents_info.append({
            "name": name,
            "class": agent.__class__.__name__,
            "signal_type": getattr(agent, 'SIGNAL_TYPE', 'unknown'),
            "event_types": list(getattr(agent, 'ALLOWED_EVENT_TYPES', set())),
        })

    return {
        "total": len(agents_info),
        "agents": agents_info,
    }


@router.get(
    "/health/signal-extraction",
    summary="Signal Extraction 건강 상태",
    description="Signal Extraction 파이프라인의 전체 건강 상태를 요약합니다.",
)
async def get_signal_extraction_health():
    """
    Signal Extraction 건강 상태 요약

    Returns:
        dict: 건강 상태 요약
    """
    # Circuit Breaker 상태
    cb_manager = get_circuit_breaker_manager()
    cb_status = cb_manager.get_all_status()

    healthy_providers = []
    degraded_providers = []
    unavailable_providers = []

    for provider, status in cb_status.items():
        if status.state == CircuitState.CLOSED:
            healthy_providers.append(provider)
        elif status.state == CircuitState.HALF_OPEN:
            degraded_providers.append(provider)
        else:
            unavailable_providers.append(provider)

    # Orchestrator 상태
    try:
        orchestrator = get_signal_orchestrator()
        orchestrator_status = "healthy"
        agent_count = len(orchestrator._agents)
    except Exception:
        orchestrator_status = "unavailable"
        agent_count = 0

    # LLM Usage
    tracker = get_usage_tracker()
    usage_summary = tracker.get_summary(last_n_minutes=60)

    # Overall health
    if unavailable_providers or orchestrator_status == "unavailable":
        overall = "unhealthy"
    elif degraded_providers:
        overall = "degraded"
    else:
        overall = "healthy"

    return {
        "status": overall,
        "components": {
            "orchestrator": {
                "status": orchestrator_status,
                "agent_count": agent_count,
            },
            "circuit_breakers": {
                "healthy": healthy_providers,
                "degraded": degraded_providers,
                "unavailable": unavailable_providers,
            },
            "llm_usage_last_hour": {
                "total_calls": usage_summary.total_calls,
                "success_rate": round(usage_summary.success_rate, 4),
                "avg_latency_ms": round(usage_summary.avg_latency_ms, 2),
            },
        },
        "capabilities": {
            "multi_agent_parallel": True,
            "cross_validation": True,
            "graceful_degradation": True,
            "distributed_execution": True,  # Celery group support
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
