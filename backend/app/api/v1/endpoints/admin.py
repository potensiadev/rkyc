"""
Admin API Endpoints

PRD v1.2:
- Circuit Breaker 상태 조회 API
- 수동 리셋 API
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.worker.llm.circuit_breaker import (
    get_circuit_breaker_manager,
    CircuitState,
)

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
