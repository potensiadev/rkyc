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
]
