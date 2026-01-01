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
    DATABASE_URL: str = Field(..., description="PostgreSQL connection string")
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_ECHO: bool = False

    # Supabase API
    SUPABASE_URL: str = Field(..., description="Supabase project URL")
    SUPABASE_ANON_KEY: str = Field(..., description="Supabase anonymous key")
    SUPABASE_SERVICE_ROLE_KEY: str = Field(..., description="Supabase service role key")

    # Redis & Celery
    REDIS_URL: str = "redis://localhost:6379/0"

    @property
    def CELERY_BROKER_URL(self) -> str:
        """Celery broker URL (uses REDIS_URL)"""
        return self.REDIS_URL

    @property
    def CELERY_RESULT_BACKEND(self) -> str:
        """Celery result backend URL (uses REDIS_URL with db 1)"""
        # Use db 1 for results if using default localhost
        if self.REDIS_URL.endswith("/0"):
            return self.REDIS_URL.replace("/0", "/1")
        return self.REDIS_URL

    # LLM Providers
    ANTHROPIC_API_KEY: str = Field(default="", description="Anthropic API key for Claude")
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API key for GPT-4o fallback")
    PERPLEXITY_API_KEY: str = Field(default="", description="Perplexity API key for external search")

    # CORS (comma-separated string, parsed in main.py)
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,https://rkyc.vercel.app"

    # Security
    SECRET_KEY: str = Field(..., min_length=32, description="Secret key for JWT")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Rate Limiting
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
