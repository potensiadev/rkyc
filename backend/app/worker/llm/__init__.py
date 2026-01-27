# LLM Integration Module
# Security Architecture: External/Internal LLM Separation
# v1.2: 2-Layer Caching (Memory LRU + Redis)

from app.worker.llm.service import LLMService
from app.worker.llm.exceptions import (
    LLMError,
    AllProvidersFailedError,
    ContentPolicyError,
    RateLimitError,
    InvalidResponseError,
    LLMTimeoutError,
    NoAPIKeyConfiguredError,
    CircuitBreakerError,
    CacheError,
    ConsensusError,
    # P1-3 Error Taxonomy
    ErrorCategory,
    ErrorSeverity,
    ErrorCode,
    ErrorContext,
    LLMErrorHandler,
    get_error_handler,
)
from app.worker.llm.cache import (
    LLMCache,
    CacheOperation,
    CacheConfig,
    MemoryLRUCache,
    get_llm_cache,
    reset_llm_cache,
)
from app.worker.llm.model_router import (
    ModelRouter,
    TaskComplexity,
    TaskType,
    ModelConfig,
    ModelTier,
    get_model_router,
    reset_model_router,
)
from app.worker.llm.cot_pipeline import (
    CoTPipeline,
    CoTStep,
    CoTStepType,
    CoTStepResult,
    CoTResult,
    SIGNAL_EXTRACTION_STEPS,
    INSIGHT_GENERATION_STEPS,
    PROFILE_EXTRACTION_STEPS,
    get_cot_pipeline,
    reset_cot_pipeline,
    # P3-2: 추론 전략 가이드
    ReasoningStrategy,
    TASK_REASONING_STRATEGY,
    get_reasoning_strategy,
)
from app.worker.llm.reflection_agent import (
    ReflectionAgent,
    ReflectionResult,
    ReflectionIteration,
    CritiqueResult,
    get_reflection_agent,
    reset_reflection_agent,
)
from app.worker.llm.shared_context import (
    SharedContextStore,
    ContextScope,
    PipelineStep,
    ContextEntry,
    LockInfo,
    get_shared_context,
    reset_shared_context,
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
    FieldThresholds,
    SourceType,
    jaccard_similarity,
    semantic_similarity,
    semantic_similarity_async,
    hybrid_similarity,
    hybrid_similarity_async,
    compare_values,
    compare_values_legacy,
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
from app.worker.llm.cache_circuit_integration import (
    CacheCircuitIntegration,
    FetchResult,
    IntegrationResult,
    get_cache_circuit,
    reset_cache_circuit,
)
from app.worker.llm.dependencies import (
    LLMDependencies,
    get_llm_service,
    get_cache,
    get_circuit_manager,
    get_model_router,
    get_cot_pipeline,
    get_reflection_agent,
    get_shared_context,
    get_consensus_engine,
    get_orchestrator,
    get_embedding_service,
    override_llm_service,
    override_cache,
    override_circuit_manager,
    override_orchestrator,
    override_consensus_engine,
    reset_all_dependencies,
    reset_dependency,
)
from app.worker.llm.agent_registry import (
    AgentRegistry,
    AgentStatus,
    AgentInfo,
    HealthCheckResult,
    get_registry,
    reset_registry,
    get_agent,
    register_agent,
    override_agent,
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

# ADR-009 Sprint 1 - Usage Tracking
from app.worker.llm.usage_tracker import (
    LLMUsageTracker,
    LLMUsageLog,
    UsageSummary,
    LLMProvider,
    TOKEN_PRICING,
    get_usage_tracker,
    reset_usage_tracker,
    log_llm_usage,
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
    "LLMTimeoutError",
    "NoAPIKeyConfiguredError",
    "CircuitBreakerError",
    "CacheError",
    "ConsensusError",
    # P1-3 Error Taxonomy
    "ErrorCategory",
    "ErrorSeverity",
    "ErrorCode",
    "ErrorContext",
    "LLMErrorHandler",
    "get_error_handler",
    # v1.2 - LLM Response Cache
    "LLMCache",
    "CacheOperation",
    "CacheConfig",
    "MemoryLRUCache",
    "get_llm_cache",
    "reset_llm_cache",
    # v1.2 - Task-Aware Model Router
    "ModelRouter",
    "TaskComplexity",
    "TaskType",
    "ModelConfig",
    "ModelTier",
    "get_model_router",
    "reset_model_router",
    # Phase 2 - Chain-of-Thought Pipeline
    "CoTPipeline",
    "CoTStep",
    "CoTStepType",
    "CoTStepResult",
    "CoTResult",
    "SIGNAL_EXTRACTION_STEPS",
    "INSIGHT_GENERATION_STEPS",
    "PROFILE_EXTRACTION_STEPS",
    "get_cot_pipeline",
    "reset_cot_pipeline",
    # P3-2: 추론 전략 가이드
    "ReasoningStrategy",
    "TASK_REASONING_STRATEGY",
    "get_reasoning_strategy",
    # Phase 2 - Reflection Agent
    "ReflectionAgent",
    "ReflectionResult",
    "ReflectionIteration",
    "CritiqueResult",
    "get_reflection_agent",
    "reset_reflection_agent",
    # Phase 2 - SharedContextStore
    "SharedContextStore",
    "ContextScope",
    "PipelineStep",
    "ContextEntry",
    "LockInfo",
    "get_shared_context",
    "reset_shared_context",
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
    # PRD v1.2 - Consensus Engine (v1.4 Hybrid Semantic)
    "ConsensusEngine",
    "ConsensusResult",
    "ConsensusMetadata",
    "FieldConsensus",
    "FieldThresholds",
    "SourceType",
    "jaccard_similarity",
    "semantic_similarity",
    "semantic_similarity_async",
    "hybrid_similarity",
    "hybrid_similarity_async",
    "compare_values",
    "compare_values_legacy",
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
    # P0-1 - Cache-Circuit Integration
    "CacheCircuitIntegration",
    "FetchResult",
    "IntegrationResult",
    "get_cache_circuit",
    "reset_cache_circuit",
    # P1-2 - FastAPI Depends DI
    "LLMDependencies",
    "get_llm_service",
    "get_cache",
    "get_circuit_manager",
    "get_model_router",
    "get_cot_pipeline",
    "get_reflection_agent",
    "get_shared_context",
    "get_consensus_engine",
    "get_orchestrator",
    "get_embedding_service",
    "override_llm_service",
    "override_cache",
    "override_circuit_manager",
    "override_orchestrator",
    "override_consensus_engine",
    "reset_all_dependencies",
    "reset_dependency",
    # P2-2 - Agent Registry
    "AgentRegistry",
    "AgentStatus",
    "AgentInfo",
    "HealthCheckResult",
    "get_registry",
    "reset_registry",
    "get_agent",
    "register_agent",
    "override_agent",
    # PRD v1.2 - Multi-Agent Orchestrator
    "MultiAgentOrchestrator",
    "OrchestratorResult",
    "FallbackLayer",
    "RuleBasedMergeConfig",
    "get_orchestrator",
    "reset_orchestrator",
    # ADR-009 Sprint 1 - Usage Tracking
    "LLMUsageTracker",
    "LLMUsageLog",
    "UsageSummary",
    "LLMProvider",
    "TOKEN_PRICING",
    "get_usage_tracker",
    "reset_usage_tracker",
    "log_llm_usage",
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
