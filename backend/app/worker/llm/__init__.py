# LLM Integration Module
# Security Architecture: External/Internal LLM Separation

from app.worker.llm.service import LLMService
from app.worker.llm.exceptions import (
    LLMError,
    AllProvidersFailedError,
    ContentPolicyError,
    RateLimitError,
    InvalidResponseError,
)

# Security Architecture Components
from app.worker.llm.internal_llm import (
    InternalLLMBase,
    InternalLLMProvider,
    DataClassification,
    MVPInternalLLM,
    AzureInternalLLM,
    OnPremLlamaLLM,
    get_internal_llm,
)
from app.worker.llm.external_llm import (
    ExternalLLMService,
    get_external_llm,
)
from app.worker.llm.embedding import (
    EmbeddingService,
    get_embedding_service,
)

# PRD v1.2 Components
from app.worker.llm.gemini_adapter import (
    GeminiAdapter,
    get_gemini_adapter,
)
from app.worker.llm.consensus_engine import (
    ConsensusEngine,
    ConsensusResult,
    ConsensusMetadata,
    FieldConsensus,
    SourceType,
    jaccard_similarity,
    compare_values,
    get_consensus_engine,
)
from app.worker.llm.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerManager,
    CircuitState,
    CircuitConfig,
    CircuitStatus,
    CircuitOpenError,
    CircuitBreakerRedisError,
    get_circuit_breaker,
    get_circuit_breaker_manager,
)

# PRD v1.2 - Multi-Agent Orchestrator
from app.worker.llm.orchestrator import (
    MultiAgentOrchestrator,
    OrchestratorResult,
    FallbackLayer,
    RuleBasedMergeConfig,
    get_orchestrator,
    reset_orchestrator,
)

__all__ = [
    # Legacy service (for backward compatibility)
    "LLMService",
    # Exceptions
    "LLMError",
    "AllProvidersFailedError",
    "ContentPolicyError",
    "RateLimitError",
    "InvalidResponseError",
    # Security Architecture - Internal LLM
    "InternalLLMBase",
    "InternalLLMProvider",
    "DataClassification",
    "MVPInternalLLM",
    "AzureInternalLLM",
    "OnPremLlamaLLM",
    "get_internal_llm",
    # Security Architecture - External LLM
    "ExternalLLMService",
    "get_external_llm",
    # Embedding
    "EmbeddingService",
    "get_embedding_service",
    # PRD v1.2 - Gemini Adapter
    "GeminiAdapter",
    "get_gemini_adapter",
    # PRD v1.2 - Consensus Engine
    "ConsensusEngine",
    "ConsensusResult",
    "ConsensusMetadata",
    "FieldConsensus",
    "SourceType",
    "jaccard_similarity",
    "compare_values",
    "get_consensus_engine",
    # PRD v1.2 - Circuit Breaker
    "CircuitBreaker",
    "CircuitBreakerManager",
    "CircuitState",
    "CircuitConfig",
    "CircuitStatus",
    "CircuitOpenError",
    "CircuitBreakerRedisError",
    "get_circuit_breaker",
    "get_circuit_breaker_manager",
    # PRD v1.2 - Multi-Agent Orchestrator
    "MultiAgentOrchestrator",
    "OrchestratorResult",
    "FallbackLayer",
    "RuleBasedMergeConfig",
    "get_orchestrator",
    "reset_orchestrator",
]
