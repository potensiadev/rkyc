"""
Signal Agents Package - Multi-Agent Signal Extraction

Sprint 2: Signal Extraction 3-Agent Split (ADR-009)
- DirectSignalAgent: 8 DIRECT event_types (기업 직접 영향)
- IndustrySignalAgent: INDUSTRY_SHOCK (산업 영향)
- EnvironmentSignalAgent: POLICY_REGULATION_CHANGE (거시환경 영향)

Sprint 3: Quality & Reliability
- Cross-Validation with conflict detection
- Graceful Degradation on agent failures
- Provider Concurrency Limits

Sprint 4: Distributed Execution
- Celery group() 분산 실행
- Admin 모니터링 API

각 Agent는 전문화된 프롬프트와 검증 로직을 가짐.
Celery group()으로 병렬 실행 후 결과 병합.
"""

# P0 Fix: Lazy imports to prevent psycopg2 dependency on module access
_LAZY_IMPORTS = {
    # base.py
    "BaseSignalAgent": "app.worker.pipelines.signal_agents.base",
    # direct_agent.py
    "DirectSignalAgent": "app.worker.pipelines.signal_agents.direct_agent",
    # industry_agent.py
    "IndustrySignalAgent": "app.worker.pipelines.signal_agents.industry_agent",
    # environment_agent.py
    "EnvironmentSignalAgent": "app.worker.pipelines.signal_agents.environment_agent",
    # orchestrator.py
    "SignalAgentOrchestrator": "app.worker.pipelines.signal_agents.orchestrator",
    "get_signal_orchestrator": "app.worker.pipelines.signal_agents.orchestrator",
    "reset_signal_orchestrator": "app.worker.pipelines.signal_agents.orchestrator",
    "AgentStatus": "app.worker.pipelines.signal_agents.orchestrator",
    "AgentResult": "app.worker.pipelines.signal_agents.orchestrator",
    "OrchestratorMetadata": "app.worker.pipelines.signal_agents.orchestrator",
    "CrossValidationResult": "app.worker.pipelines.signal_agents.orchestrator",
    "ProviderConcurrencyLimiter": "app.worker.pipelines.signal_agents.orchestrator",
    "get_concurrency_limiter": "app.worker.pipelines.signal_agents.orchestrator",
    "execute_distributed": "app.worker.pipelines.signal_agents.orchestrator",
}


def __getattr__(name):
    """Lazy import to prevent psycopg2 dependency on module access."""
    if name in _LAZY_IMPORTS:
        module_path = _LAZY_IMPORTS[name]
        import importlib
        module = importlib.import_module(module_path)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Agents
    "BaseSignalAgent",
    "DirectSignalAgent",
    "IndustrySignalAgent",
    "EnvironmentSignalAgent",
    # Orchestrator
    "SignalAgentOrchestrator",
    "get_signal_orchestrator",
    "reset_signal_orchestrator",
    # Sprint 3: Data classes
    "AgentStatus",
    "AgentResult",
    "OrchestratorMetadata",
    "CrossValidationResult",
    # Sprint 3: Concurrency limiter
    "ProviderConcurrencyLimiter",
    "get_concurrency_limiter",
    # Sprint 4: Distributed execution
    "execute_distributed",
]
