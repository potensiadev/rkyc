"""
Synchronous Database Access for Celery Workers
Celery tasks are synchronous, so we need a sync database session
"""

from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import settings

# Convert async DATABASE_URL to sync format
# asyncpg:// -> postgresql://
sync_database_url = settings.DATABASE_URL.replace(
    "postgresql+asyncpg://", "postgresql://"
).replace(
    "postgres://", "postgresql://"
)

# Create synchronous engine
sync_engine = create_engine(
    sync_database_url,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    # pgbouncer compatibility
    connect_args={
        "options": "-c statement_timeout=30000"  # 30 second timeout
    }
)

# Create session factory
SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
)


@contextmanager
def get_sync_db() -> Session:
    """
    Get a synchronous database session for Celery tasks.

    Usage:
        with get_sync_db() as db:
            result = db.execute(query)
    """
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_sync_session() -> Session:
    """
    Get a raw session (caller responsible for closing).
    Use get_sync_db() context manager when possible.
    """
    return SyncSessionLocal()
