"""
rKYC Database Connection
SQLAlchemy async engine and session management for Supabase PostgreSQL
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import declarative_base
from app.core.config import settings

# Create async engine
# Note: asyncpg driver is used (postgresql+asyncpg://)
# statement_cache_size=0 is required for Supabase Transaction pooler (pgbouncer)
engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=True,  # Verify connections before using
    echo=settings.DB_ECHO,  # Log SQL queries if DEBUG
    future=True,
    connect_args={
        "statement_cache_size": 0,  # Disable prepared statement cache for pgbouncer
        "prepared_statement_cache_size": 0,
    },
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
