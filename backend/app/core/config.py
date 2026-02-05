"""
rKYC Application Configuration
Pydantic Settings for environment variable management
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Application
    APP_NAME: str = "rKYC"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database (Supabase PostgreSQL)
    # Note: Supabase free tier has limited connections (~20 total)
    # Using conservative pool size to avoid connection exhaustion
    DATABASE_URL: str = Field(..., description="PostgreSQL connection string")
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 5
    DB_ECHO: bool = False

    # Supabase API
    SUPABASE_URL: str = Field(..., description="Supabase project URL")
    SUPABASE_ANON_KEY: str = Field(..., description="Supabase anonymous key")
    SUPABASE_SERVICE_ROLE_KEY: str = Field(..., description="Supabase service role key")

    # Redis & Celery
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_BROKER_DB: int = Field(default=0, description="Redis DB number for Celery broker")
    REDIS_RESULT_DB: int = Field(default=1, description="Redis DB number for Celery results")

    # =========================================================================
    # Circuit Breaker Configuration (P1-1)
    # =========================================================================
    CIRCUIT_BREAKER_REQUIRE_REDIS: bool = Field(
        default=True,
        description="Require Redis for circuit breaker state persistence (recommended for production)"
    )
    # Provider-specific settings (JSON format: {"provider": {"threshold": 3, "cooldown": 300}})
    CIRCUIT_BREAKER_PERPLEXITY_THRESHOLD: int = Field(default=3, description="Perplexity failure threshold")
    CIRCUIT_BREAKER_PERPLEXITY_COOLDOWN: int = Field(default=300, description="Perplexity cooldown seconds")
    CIRCUIT_BREAKER_GEMINI_THRESHOLD: int = Field(default=3, description="Gemini failure threshold")
    CIRCUIT_BREAKER_GEMINI_COOLDOWN: int = Field(default=300, description="Gemini cooldown seconds")
    CIRCUIT_BREAKER_CLAUDE_THRESHOLD: int = Field(default=2, description="Claude failure threshold (more conservative)")
    CIRCUIT_BREAKER_CLAUDE_COOLDOWN: int = Field(default=600, description="Claude cooldown seconds")
    CIRCUIT_BREAKER_OPENAI_THRESHOLD: int = Field(default=3, description="OpenAI failure threshold")
    CIRCUIT_BREAKER_OPENAI_COOLDOWN: int = Field(default=300, description="OpenAI cooldown seconds")

    # =========================================================================
    # LLM Cache Configuration (P1-1)
    # =========================================================================
    LLM_CACHE_REDIS_DB: int = Field(default=2, description="Redis DB number for LLM cache")
    LLM_CACHE_MEMORY_SIZE: int = Field(default=100, description="Memory LRU cache size per operation")
    # TTL settings (seconds)
    LLM_CACHE_TTL_PROFILE: int = Field(default=604800, description="Profile extraction cache TTL (7 days)")
    LLM_CACHE_TTL_SIGNAL: int = Field(default=86400, description="Signal extraction cache TTL (1 day)")
    LLM_CACHE_TTL_VALIDATION: int = Field(default=3600, description="Validation cache TTL (1 hour)")
    LLM_CACHE_TTL_EMBEDDING: int = Field(default=2592000, description="Embedding cache TTL (30 days)")
    LLM_CACHE_TTL_CONSENSUS: int = Field(default=86400, description="Consensus cache TTL (1 day)")
    LLM_CACHE_TTL_DOCUMENT: int = Field(default=604800, description="Document parsing cache TTL (7 days)")
    LLM_CACHE_TTL_INSIGHT: int = Field(default=43200, description="Insight generation cache TTL (12 hours)")

    # =========================================================================
    # Model Router Configuration (P1-1)
    # =========================================================================
    # Simple tier models (fast, cost-effective)
    MODEL_SIMPLE_PRIMARY: str = Field(default="claude-3-5-haiku-20241022", description="Primary simple model")
    MODEL_SIMPLE_FALLBACK: str = Field(default="gpt-4o-mini", description="Fallback simple model")
    # Moderate tier models (balanced)
    MODEL_MODERATE_PRIMARY: str = Field(default="claude-sonnet-4-20250514", description="Primary moderate model")
    MODEL_MODERATE_FALLBACK1: str = Field(default="gpt-4o", description="First fallback moderate model")
    MODEL_MODERATE_FALLBACK2: str = Field(default="gemini/gemini-2.0-flash", description="Second fallback moderate model")
    # Complex tier models (high quality)
    MODEL_COMPLEX_PRIMARY: str = Field(default="claude-opus-4-5-20251101", description="Primary complex model")
    MODEL_COMPLEX_FALLBACK1: str = Field(default="gpt-4o", description="First fallback complex model")
    MODEL_COMPLEX_FALLBACK2: str = Field(default="gemini/gemini-3-pro-preview", description="Second fallback complex model")

    # =========================================================================
    # Consensus Engine Configuration (P2-3)
    # =========================================================================
    CONSENSUS_SIMILARITY_THRESHOLD: float = Field(default=0.7, description="Default similarity threshold")
    CONSENSUS_THRESHOLD_NUMBER: float = Field(default=0.1, description="Numeric comparison threshold (10%)")
    CONSENSUS_THRESHOLD_NAME: float = Field(default=0.9, description="Name/entity comparison threshold")
    CONSENSUS_THRESHOLD_SUMMARY: float = Field(default=0.6, description="Summary/description threshold")
    CONSENSUS_USE_SEMANTIC: bool = Field(default=True, description="Enable semantic similarity")

    @property
    def CELERY_BROKER_URL(self) -> str:
        """Celery broker URL (uses REDIS_URL with REDIS_BROKER_DB)"""
        base_url = self.REDIS_URL.rstrip("/0123456789")
        return f"{base_url}/{self.REDIS_BROKER_DB}"

    @property
    def CELERY_RESULT_BACKEND(self) -> str:
        """Celery result backend URL (uses REDIS_URL with REDIS_RESULT_DB)"""
        base_url = self.REDIS_URL.rstrip("/0123456789")
        return f"{base_url}/{self.REDIS_RESULT_DB}"

    # LLM Retry Configuration
    LLM_MAX_RETRIES: int = Field(default=3, description="Maximum retry attempts for LLM calls")
    LLM_INITIAL_DELAY: float = Field(default=1.0, description="Initial retry delay in seconds")
    LLM_MAX_DELAY: float = Field(default=60.0, description="Maximum retry delay in seconds")
    LLM_BACKOFF_MULTIPLIER: float = Field(default=2.0, description="Exponential backoff multiplier")
    LLM_VERBOSE: bool = Field(default=False, description="Enable verbose LLM logging (litellm)")

    # Embedding Configuration
    EMBEDDING_MAX_BATCH_SIZE: int = Field(default=100, description="Max batch size for embedding API")
    EMBEDDING_MAX_RETRIES: int = Field(default=3, description="Max retries for embedding API")

    # Document Storage
    DOCUMENT_STORAGE_PATH: str = Field(default="./data/documents", description="Path for document storage")

    # LLM Providers (Legacy - used by both External/Internal in MVP)
    ANTHROPIC_API_KEY: str = Field(default="", description="Anthropic API key for Claude")
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API key for GPT-4o fallback")
    GOOGLE_API_KEY: str = Field(default="", description="Google API key for Gemini fallback")
    PERPLEXITY_API_KEY: str = Field(default="", description="Perplexity API key for external search")

    # =========================================================================
    # API Key Rotation (다중 키 지원)
    # =========================================================================
    # Perplexity 다중 키 (로테이션용)
    PERPLEXITY_API_KEY_1: str = Field(default="", description="Perplexity API key 1")
    PERPLEXITY_API_KEY_2: str = Field(default="", description="Perplexity API key 2")
    PERPLEXITY_API_KEY_3: str = Field(default="", description="Perplexity API key 3")
    # Google 다중 키 (로테이션용)
    GOOGLE_API_KEY_1: str = Field(default="", description="Google API key 1")
    GOOGLE_API_KEY_2: str = Field(default="", description="Google API key 2")
    GOOGLE_API_KEY_3: str = Field(default="", description="Google API key 3")
    # 키 로테이션 설정
    KEY_ROTATION_ENABLED: bool = Field(default=True, description="Enable API key rotation")
    KEY_ROTATION_FAILURE_COOLDOWN: int = Field(default=300, description="Cooldown seconds for failed key")

    # =========================================================================
    # Multi-Search Provider Configuration (검색 내장 LLM 2-Track)
    # =========================================================================
    # 검색 가능 LLM: Perplexity, Gemini (OpenAI/Claude는 검색 기능 없음)
    SEARCH_PROVIDER_PRIORITY: str = Field(
        default="perplexity,gemini_grounding",
        description="Search provider priority (LLMs with built-in search only)"
    )
    # Multi-Search 병렬 모드 (Perplexity + Gemini 동시 검색)
    MULTI_SEARCH_PARALLEL_MODE: bool = Field(default=False, description="Enable parallel search with both providers")

    # Security Architecture: Internal LLM Configuration
    # INTERNAL_LLM_PROVIDER: mvp_openai (default) | azure_openai | onprem_llama
    INTERNAL_LLM_PROVIDER: str = Field(default="mvp_openai", description="Internal LLM provider selection")
    INTERNAL_LLM_OPENAI_KEY: str = Field(default="", description="OpenAI key for Internal LLM (MVP)")
    INTERNAL_LLM_ANTHROPIC_KEY: str = Field(default="", description="Anthropic key for Internal LLM (MVP backup)")
    # Phase 2: Azure OpenAI
    INTERNAL_LLM_AZURE_ENDPOINT: str = Field(default="", description="Azure OpenAI endpoint (Phase 2)")
    INTERNAL_LLM_AZURE_DEPLOYMENT: str = Field(default="gpt-4", description="Azure deployment name")
    INTERNAL_LLM_AZURE_API_VERSION: str = Field(default="2024-02-15-preview", description="Azure API version")
    # Phase 3: On-Premise
    INTERNAL_LLM_ONPREM_ENDPOINT: str = Field(default="", description="On-premise LLM endpoint (Phase 3)")

    # Security Architecture: External LLM Configuration (optional separate keys)
    EXTERNAL_LLM_ANTHROPIC_KEY: str = Field(default="", description="Anthropic key for External LLM (optional)")
    EXTERNAL_LLM_OPENAI_KEY: str = Field(default="", description="OpenAI key for External LLM (optional)")
    EXTERNAL_LLM_PERPLEXITY_KEY: str = Field(default="", description="Perplexity key for External LLM (optional)")

    # CORS (comma-separated string, parsed in main.py)
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,https://rkyc.vercel.app"

    # Rate Limiting (for future implementation)
    RATE_LIMIT_PER_MINUTE: int = 60

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.ENVIRONMENT == "production"


# Global settings instance
settings = Settings()
