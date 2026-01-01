"""
rKYC Database Connection
SQLAlchemy async engine and session management for Supabase PostgreSQL
"""

import ssl
from typing import AsyncGenerator
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import declarative_base
from app.core.config import settings


def _prepare_database_url(url: str) -> tuple[str, dict]:
    """
    Prepare DATABASE_URL for asyncpg driver.

    asyncpg doesn't support 'sslmode' query parameter directly.
    We need to:
    1. Remove sslmode from URL
    2. Return ssl context in connect_args
    """
    # Parse the URL
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)

    # Check if sslmode is present
    ssl_mode = query_params.pop("sslmode", [None])[0]

    # Rebuild URL without sslmode
    new_query = urlencode(query_params, doseq=True)
    new_parsed = parsed._replace(query=new_query)
    clean_url = urlunparse(new_parsed)

    # Convert to asyncpg format
    clean_url = clean_url.replace("postgresql://", "postgresql+asyncpg://")

    # Build connect_args
    connect_args = {
        "statement_cache_size": 0,  # Disable prepared statement cache for pgbouncer
        "prepared_statement_cache_size": 0,
    }

    # Add SSL if sslmode was require
    if ssl_mode in ("require", "verify-ca", "verify-full"):
        # Create SSL context for asyncpg
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE  # Supabase uses self-signed certs
        connect_args["ssl"] = ssl_context

    return clean_url, connect_args


# Prepare database URL and SSL settings
_database_url, _connect_args = _prepare_database_url(settings.DATABASE_URL)

# Create async engine
# Note: asyncpg driver is used (postgresql+asyncpg://)
# statement_cache_size=0 is required for Supabase Transaction pooler (pgbouncer)
engine = create_async_engine(
    _database_url,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=True,  # Verify connections before using
    echo=settings.DB_ECHO,  # Log SQL queries if DEBUG
    future=True,
    connect_args=_connect_args,
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Declarative base for models
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI routes to get database session

    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database (create tables if needed)"""
    async with engine.begin() as conn:
        # Note: For Supabase, we manage schema via SQL files
        # This is here for future migrations if needed
        # await conn.run_sync(Base.metadata.create_all)
        pass


async def close_db():
    """Close database connection pool"""
    await engine.dispose()
