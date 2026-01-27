"""
Agent Registry for rKYC Multi-Agent System

P2-2: Central Agent Registry Pattern

특징:
- 모든 Agent를 중앙에서 관리
- Agent 교체 용이 (A/B 테스트, Mock 주입)
- 의존성 명시화
- Health check 지원

Usage:
    from app.worker.llm.agent_registry import AgentRegistry, get_registry

    # Registry 조회
    registry = get_registry()

    # Agent 등록
    registry.register("llm_service", LLMService, factory=lambda: LLMService())

    # Agent 조회
    llm = registry.get("llm_service")

    # Mock 주입 (테스트)
    with registry.override("llm_service", mock_llm):
        result = await some_function()

    # Health check
    status = await registry.health_check()
"""

import threading
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Callable, Dict, Optional, Type, TypeVar, Generic
from enum import Enum

from app.worker.tracing import get_logger

logger = get_logger("AgentRegistry")

T = TypeVar("T")


class AgentStatus(str, Enum):
    """Agent health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class AgentInfo:
    """Information about a registered agent"""
    name: str
    agent_type: Type
    instance: Optional[Any] = None
    factory: Optional[Callable[[], Any]] = None
    singleton: bool = True
    status: AgentStatus = AgentStatus.UNKNOWN
    last_health_check: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class HealthCheckResult:
    """Result of a health check"""
    name: str
    status: AgentStatus
    message: Optional[str] = None
    latency_ms: Optional[int] = None
    details: dict = field(default_factory=dict)


class AgentRegistry:
    """
    Central registry for all LLM agents.

    Features:
    - Singleton or factory-based agent creation
    - Override support for testing
    - Health check integration
    - Lazy initialization
    """

    def __init__(self):
        self._agents: Dict[str, AgentInfo] = {}
        self._overrides: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._initialized = False

    def register(
        self,
        name: str,
        agent_type: Type[T],
        factory: Optional[Callable[[], T]] = None,
        instance: Optional[T] = None,
        singleton: bool = True,
        metadata: Optional[dict] = None,
    ) -> None:
        """
        Register an agent.

        Args:
            name: Unique agent name
            agent_type: Agent class type
            factory: Factory function to create agent (optional)
            instance: Pre-created instance (optional)
            singleton: If True, use same instance for all requests
            metadata: Additional metadata
        """
        with self._lock:
            if name in self._agents:
                logger.warning(f"Overwriting existing agent registration: {name}")

            self._agents[name] = AgentInfo(
                name=name,
                agent_type=agent_type,
                instance=instance,
                factory=factory,
                singleton=singleton,
                metadata=metadata or {},
            )

            logger.debug(f"Registered agent: {name} (type={agent_type.__name__})")

    def get(self, name: str) -> Any:
        """
        Get an agent by name.

        Args:
            name: Agent name

        Returns:
            Agent instance

        Raises:
            KeyError: If agent not found
        """
        # Check override first
        if name in self._overrides:
            return self._overrides[name]

        with self._lock:
            if name not in self._agents:
                # Try to auto-register known agents
                self._auto_register(name)

            if name not in self._agents:
                raise KeyError(f"Agent not found: {name}")

            info = self._agents[name]

            # Return existing instance for singletons
            if info.singleton and info.instance is not None:
                return info.instance

            # Create new instance
            if info.factory:
                instance = info.factory()
            else:
                instance = info.agent_type()

            # Store instance for singletons
            if info.singleton:
                info.instance = instance

            return instance

    def _auto_register(self, name: str) -> None:
        """Auto-register known agents on first access."""
        auto_registrations = {
            "llm_service": ("app.worker.llm.service", "LLMService"),
            "cache": ("app.worker.llm.cache", "LLMCache"),
            "circuit_manager": ("app.worker.llm.circuit_breaker", "CircuitBreakerManager"),
            "model_router": ("app.worker.llm.model_router", "ModelRouter"),
            "cot_pipeline": ("app.worker.llm.cot_pipeline", "CoTPipeline"),
            "reflection_agent": ("app.worker.llm.reflection_agent", "ReflectionAgent"),
            "shared_context": ("app.worker.llm.shared_context", "SharedContextStore"),
            "consensus_engine": ("app.worker.llm.consensus_engine", "ConsensusEngine"),
            "orchestrator": ("app.worker.llm.orchestrator", "MultiAgentOrchestrator"),
            "embedding_service": ("app.worker.llm.embedding", "EmbeddingService"),
            "cache_circuit": ("app.worker.llm.cache_circuit_integration", "CacheCircuitIntegration"),
        }

        if name in auto_registrations:
            module_path, class_name = auto_registrations[name]
            try:
                import importlib
                module = importlib.import_module(module_path)
                agent_type = getattr(module, class_name)
                self.register(name, agent_type)
                logger.debug(f"Auto-registered agent: {name}")
            except Exception as e:
                logger.warning(f"Failed to auto-register agent {name}: {e}")

    def has(self, name: str) -> bool:
        """Check if an agent is registered."""
        return name in self._agents or name in self._overrides

    def list_agents(self) -> list[str]:
        """List all registered agent names."""
        with self._lock:
            return list(self._agents.keys())

    def get_info(self, name: str) -> Optional[AgentInfo]:
        """Get agent info by name."""
        with self._lock:
            return self._agents.get(name)

    @contextmanager
    def override(self, name: str, instance: Any):
        """
        Override an agent for testing.

        Usage:
            with registry.override("llm_service", mock_llm):
                result = await function_using_llm()
        """
        self._overrides[name] = instance
        logger.debug(f"Overriding agent: {name}")
        try:
            yield instance
        finally:
            del self._overrides[name]
            logger.debug(f"Removed override for agent: {name}")

    def clear_override(self, name: str) -> None:
        """Clear a specific override."""
        self._overrides.pop(name, None)

    def clear_all_overrides(self) -> None:
        """Clear all overrides."""
        self._overrides.clear()

    async def health_check(self, name: Optional[str] = None) -> Dict[str, HealthCheckResult]:
        """
        Perform health check on agents.

        Args:
            name: Specific agent name, or None for all agents

        Returns:
            Dict of health check results
        """
        import time

        results = {}

        agents_to_check = [name] if name else list(self._agents.keys())

        for agent_name in agents_to_check:
            start_time = time.time()
            try:
                agent = self.get(agent_name)

                # Check if agent has a health check method
                if hasattr(agent, "health_check"):
                    status = await agent.health_check()
                    agent_status = AgentStatus.HEALTHY if status else AgentStatus.UNHEALTHY
                elif hasattr(agent, "is_available"):
                    is_available = agent.is_available
                    if callable(is_available):
                        is_available = is_available()
                    agent_status = AgentStatus.HEALTHY if is_available else AgentStatus.DEGRADED
                else:
                    # Basic check - agent exists and is instantiated
                    agent_status = AgentStatus.HEALTHY

                latency_ms = int((time.time() - start_time) * 1000)

                results[agent_name] = HealthCheckResult(
                    name=agent_name,
                    status=agent_status,
                    latency_ms=latency_ms,
                )

                # Update agent info
                with self._lock:
                    if agent_name in self._agents:
                        self._agents[agent_name].status = agent_status
                        self._agents[agent_name].last_health_check = datetime.now(UTC).isoformat()

            except Exception as e:
                latency_ms = int((time.time() - start_time) * 1000)
                results[agent_name] = HealthCheckResult(
                    name=agent_name,
                    status=AgentStatus.UNHEALTHY,
                    message=str(e),
                    latency_ms=latency_ms,
                )

        return results

    def reset(self, name: Optional[str] = None) -> None:
        """
        Reset agent instance(s).

        Args:
            name: Specific agent name, or None for all agents
        """
        with self._lock:
            if name:
                if name in self._agents:
                    self._agents[name].instance = None
                    logger.debug(f"Reset agent: {name}")
            else:
                for info in self._agents.values():
                    info.instance = None
                logger.debug("Reset all agents")

    def reset_all(self) -> None:
        """Reset all agents and overrides."""
        with self._lock:
            for info in self._agents.values():
                info.instance = None
            self._overrides.clear()
            logger.info("Reset all agents and overrides")


# ============================================================================
# Singleton Instance
# ============================================================================

_registry_instance: Optional[AgentRegistry] = None
_registry_lock = threading.Lock()


def get_registry() -> AgentRegistry:
    """
    Get singleton AgentRegistry instance.

    Thread-safe with double-checked locking.
    """
    global _registry_instance

    # Fast path
    if _registry_instance is not None:
        return _registry_instance

    # Slow path with lock
    with _registry_lock:
        if _registry_instance is None:
            _registry_instance = AgentRegistry()
            logger.info("AgentRegistry singleton initialized")

    return _registry_instance


def reset_registry() -> None:
    """Reset the singleton registry (for testing)."""
    global _registry_instance
    with _registry_lock:
        if _registry_instance:
            _registry_instance.reset_all()
        _registry_instance = None
        logger.info("AgentRegistry singleton reset")


# ============================================================================
# Convenience Functions
# ============================================================================

def get_agent(name: str) -> Any:
    """Convenience function to get an agent from the registry."""
    return get_registry().get(name)


def register_agent(
    name: str,
    agent_type: Type,
    factory: Optional[Callable] = None,
    **kwargs,
) -> None:
    """Convenience function to register an agent."""
    get_registry().register(name, agent_type, factory=factory, **kwargs)


@contextmanager
def override_agent(name: str, instance: Any):
    """Convenience function to override an agent."""
    with get_registry().override(name, instance):
        yield instance
