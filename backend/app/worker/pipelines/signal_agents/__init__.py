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

from app.worker.pipelines.signal_agents.base import BaseSignalAgent
from app.worker.pipelines.signal_agents.direct_agent import DirectSignalAgent
from app.worker.pipelines.signal_agents.industry_agent import IndustrySignalAgent
from app.worker.pipelines.signal_agents.environment_agent import EnvironmentSignalAgent
from app.worker.pipelines.signal_agents.orchestrator import (
    SignalAgentOrchestrator,
    get_signal_orchestrator,
    reset_signal_orchestrator,
    # Sprint 3: Data classes
    AgentStatus,
    AgentResult,
    OrchestratorMetadata,
    CrossValidationResult,
    # Sprint 3: Concurrency limiter
    ProviderConcurrencyLimiter,
    get_concurrency_limiter,
    # Sprint 4: Distributed execution
    execute_distributed,
)

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
