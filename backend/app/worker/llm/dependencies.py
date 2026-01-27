"""
LLM Service Dependencies for FastAPI and Celery

P1-2: FastAPI Depends 패턴 기반 의존성 주입

특징:
- FastAPI Depends와 호환
- Celery Worker에서도 사용 가능
- 테스트 시 Mock 주입 용이
- Singleton 패턴 제거, Depends 패턴으로 전환

Usage (FastAPI):
    from app.worker.llm.dependencies import get_llm_service, get_cache, get_circuit_manager

    @router.post("/analyze")
    async def analyze(
        llm: LLMService = Depends(get_llm_service),
        cache: LLMCache = Depends(get_cache),
    ):
        ...

Usage (Celery/Worker):
    from app.worker.llm.dependencies import LLMDependencies

    deps = LLMDependencies()
    llm = deps.llm_service
    cache = deps.cache

Usage (Testing):
    from app.worker.llm.dependencies import override_llm_service

    # Override for testing
    with override_llm_service(mock_llm):
        result = await some_function()
"""

import threading
from contextlib import contextmanager
from typing import Optional, Generator, Any, Callable
from functools import lru_cache

from app.worker.tracing import get_logger

logger = get_logger("LLMDependencies")


# ============================================================================
# Thread-safe instance storage
# ============================================================================

class _InstanceRegistry:
    """Thread-safe instance registry for DI"""

    def __init__(self):
        self._instances: dict[str, Any] = {}
        self._overrides: dict[str, Any] = {}
        self._lock = threading.Lock()

    def get(self, key: str, factory: Callable[[], Any]) -> Any:
        """Get or create instance (thread-safe)"""
        # Check for override first
        if key in self._overrides:
            return self._overrides[key]

        # Fast path without lock
        if key in self._instances:
            return self._instances[key]

        # Slow path with lock
        with self._lock:
            if key not in self._instances:
                self._instances[key] = factory()
                logger.debug(f"Created instance: {key}")
            return self._instances[key]

    def override(self, key: str, instance: Any) -> None:
        """Override instance (for testing)"""
        with self._lock:
            self._overrides[key] = instance
            logger.debug(f"Overridden instance: {key}")

    def clear_override(self, key: str) -> None:
        """Clear override"""
        with self._lock:
            self._overrides.pop(key, None)
            logger.debug(f"Cleared override: {key}")

    def clear_all(self) -> None:
        """Clear all instances and overrides (for testing)"""
        with self._lock:
            self._instances.clear()
            self._overrides.clear()
            logger.debug("Cleared all instances and overrides")

    def reset(self, key: str) -> None:
        """Reset a specific instance"""
        with self._lock:
            self._instances.pop(key, None)
            self._overrides.pop(key, None)


_registry = _InstanceRegistry()


# ============================================================================
# Factory Functions
# ============================================================================

def _create_llm_service():
    """Factory for LLMService"""
    from app.worker.llm.service import LLMService
    return LLMService()


def _create_cache():
    """Factory for LLMCache"""
    from app.worker.llm.cache import LLMCache
    return LLMCache()


def _create_circuit_manager():
    """Factory for CircuitBreakerManager"""
    from app.worker.llm.circuit_breaker import CircuitBreakerManager
    return CircuitBreakerManager()


def _create_model_router():
    """Factory for ModelRouter"""
    from app.worker.llm.model_router import ModelRouter
    return ModelRouter()


def _create_cot_pipeline():
    """Factory for CoTPipeline"""
    from app.worker.llm.cot_pipeline import CoTPipeline
    return CoTPipeline()


def _create_reflection_agent():
    """Factory for ReflectionAgent"""
    from app.worker.llm.reflection_agent import ReflectionAgent
    return ReflectionAgent()


def _create_shared_context():
    """Factory for SharedContextStore"""
    from app.worker.llm.shared_context import SharedContextStore
    return SharedContextStore()


def _create_consensus_engine():
    """Factory for ConsensusEngine"""
    from app.worker.llm.consensus_engine import ConsensusEngine
    return ConsensusEngine()


def _create_orchestrator():
    """Factory for MultiAgentOrchestrator"""
    from app.worker.llm.orchestrator import MultiAgentOrchestrator
    return MultiAgentOrchestrator()


def _create_embedding_service():
    """Factory for EmbeddingService"""
    from app.worker.llm.embedding import EmbeddingService
    return EmbeddingService()


def _create_cache_circuit_integration():
    """Factory for CacheCircuitIntegration"""
    from app.worker.llm.cache_circuit_integration import CacheCircuitIntegration
    return CacheCircuitIntegration()


# ============================================================================
# FastAPI Depends compatible functions
# ============================================================================

def get_llm_service():
    """
    Get LLMService instance.

    FastAPI Depends compatible.
    """
    return _registry.get("llm_service", _create_llm_service)


def get_cache():
    """
    Get LLMCache instance.

    FastAPI Depends compatible.
    """
    return _registry.get("cache", _create_cache)


def get_circuit_manager():
    """
    Get CircuitBreakerManager instance.

    FastAPI Depends compatible.
    """
    return _registry.get("circuit_manager", _create_circuit_manager)


def get_model_router():
    """
    Get ModelRouter instance.

    FastAPI Depends compatible.
    """
    return _registry.get("model_router", _create_model_router)


def get_cot_pipeline():
    """
    Get CoTPipeline instance.

    FastAPI Depends compatible.
    """
    return _registry.get("cot_pipeline", _create_cot_pipeline)


def get_reflection_agent():
    """
    Get ReflectionAgent instance.

    FastAPI Depends compatible.
    """
    return _registry.get("reflection_agent", _create_reflection_agent)


def get_shared_context():
    """
    Get SharedContextStore instance.

    FastAPI Depends compatible.
    """
    return _registry.get("shared_context", _create_shared_context)


def get_consensus_engine():
    """
    Get ConsensusEngine instance.

    FastAPI Depends compatible.
    """
    return _registry.get("consensus_engine", _create_consensus_engine)


def get_orchestrator():
    """
    Get MultiAgentOrchestrator instance.

    FastAPI Depends compatible.
    """
    return _registry.get("orchestrator", _create_orchestrator)


def get_embedding_service():
    """
    Get EmbeddingService instance.

    FastAPI Depends compatible.
    """
    return _registry.get("embedding_service", _create_embedding_service)


def get_cache_circuit():
    """
    Get CacheCircuitIntegration instance.

    FastAPI Depends compatible.
    """
    return _registry.get("cache_circuit", _create_cache_circuit_integration)


# ============================================================================
# Override Context Managers (for testing)
# ============================================================================

@contextmanager
def override_llm_service(mock_instance):
    """Override LLMService for testing"""
    _registry.override("llm_service", mock_instance)
    try:
        yield mock_instance
    finally:
        _registry.clear_override("llm_service")


@contextmanager
def override_cache(mock_instance):
    """Override LLMCache for testing"""
    _registry.override("cache", mock_instance)
    try:
        yield mock_instance
    finally:
        _registry.clear_override("cache")


@contextmanager
def override_circuit_manager(mock_instance):
    """Override CircuitBreakerManager for testing"""
    _registry.override("circuit_manager", mock_instance)
    try:
        yield mock_instance
    finally:
        _registry.clear_override("circuit_manager")


@contextmanager
def override_orchestrator(mock_instance):
    """Override MultiAgentOrchestrator for testing"""
    _registry.override("orchestrator", mock_instance)
    try:
        yield mock_instance
    finally:
        _registry.clear_override("orchestrator")


@contextmanager
def override_consensus_engine(mock_instance):
    """Override ConsensusEngine for testing"""
    _registry.override("consensus_engine", mock_instance)
    try:
        yield mock_instance
    finally:
        _registry.clear_override("consensus_engine")


# ============================================================================
# LLMDependencies Class (for Celery/Worker usage)
# ============================================================================

class LLMDependencies:
    """
    Convenience class for accessing all LLM dependencies.

    Useful in Celery tasks and other non-FastAPI contexts.

    Usage:
        deps = LLMDependencies()
        result = deps.llm_service.call_with_fallback(messages)
    """

    @property
    def llm_service(self):
        return get_llm_service()

    @property
    def cache(self):
        return get_cache()

    @property
    def circuit_manager(self):
        return get_circuit_manager()

    @property
    def model_router(self):
        return get_model_router()

    @property
    def cot_pipeline(self):
        return get_cot_pipeline()

    @property
    def reflection_agent(self):
        return get_reflection_agent()

    @property
    def shared_context(self):
        return get_shared_context()

    @property
    def consensus_engine(self):
        return get_consensus_engine()

    @property
    def orchestrator(self):
        return get_orchestrator()

    @property
    def embedding_service(self):
        return get_embedding_service()

    @property
    def cache_circuit(self):
        return get_cache_circuit()


# ============================================================================
# Reset functions (for testing)
# ============================================================================

def reset_all_dependencies():
    """Reset all dependencies (for testing)"""
    _registry.clear_all()
    logger.info("All LLM dependencies reset")


def reset_dependency(name: str):
    """Reset a specific dependency (for testing)"""
    _registry.reset(name)
    logger.info(f"LLM dependency reset: {name}")
