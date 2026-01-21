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

# v2.0 - 4-Layer Analysis Architecture
from app.worker.llm.layer_architecture import (
    # Enums and Constants
    SourceCredibility,
    ImpactPath,
    ConfidenceLevel,
    CREDIBILITY_CRITERIA,
    # Data Classes
    IntakeOutput,
    EvidenceEntry,
    EvidenceMapOutput,
    CorporationAnalysis,
    SignalAnalysis,
    QualityGateOutput,
    # Null-Free Policy
    NullFreePolicy,
    # Layer Implementations
    IntakeLayer,
    EvidenceLayer,
    ExpertAnalysisLayer,
    QualityGateLayer,
    # Main Orchestrator
    FourLayerAnalysisPipeline,
)

# v2.0 - Enhanced Prompts
from app.worker.llm.prompts_v2 import (
    EXPERT_ANALYSIS_SYSTEM_PROMPT,
    CORPORATION_ANALYSIS_PROMPT,
    SIGNAL_ANALYSIS_PROMPT,
    EVIDENCE_MAP_PROMPT,
    INSIGHT_GENERATION_PROMPT_V2,
    NULL_FREE_RULES,
    format_corporation_analysis_prompt,
    format_signal_analysis_prompt,
    format_evidence_map_prompt,
    format_insight_prompt_v2,
    get_industry_context,
    INDUSTRY_CONTEXT,
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
    # v2.0 - 4-Layer Analysis Architecture
    "SourceCredibility",
    "ImpactPath",
    "ConfidenceLevel",
    "CREDIBILITY_CRITERIA",
    "IntakeOutput",
    "EvidenceEntry",
    "EvidenceMapOutput",
    "CorporationAnalysis",
    "SignalAnalysis",
    "QualityGateOutput",
    "NullFreePolicy",
    "IntakeLayer",
    "EvidenceLayer",
    "ExpertAnalysisLayer",
    "QualityGateLayer",
    "FourLayerAnalysisPipeline",
    # v2.0 - Enhanced Prompts
    "EXPERT_ANALYSIS_SYSTEM_PROMPT",
    "CORPORATION_ANALYSIS_PROMPT",
    "SIGNAL_ANALYSIS_PROMPT",
    "EVIDENCE_MAP_PROMPT",
    "INSIGHT_GENERATION_PROMPT_V2",
    "NULL_FREE_RULES",
    "format_corporation_analysis_prompt",
    "format_signal_analysis_prompt",
    "format_evidence_map_prompt",
    "format_insight_prompt_v2",
    "get_industry_context",
    "INDUSTRY_CONTEXT",
]
