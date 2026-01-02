"""
Synchronous Database Access for Celery Workers
Celery tasks are synchronous, so we need a sync database session
"""

from contextlib import contextmanager
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import settings


def _prepare_sync_database_url(url: str) -> tuple[str, dict]:
    """
    Prepare DATABASE_URL for psycopg2 driver (sync).

    Unlike asyncpg, psycopg2 supports sslmode in URL.
    We just need to convert the protocol and ensure proper SSL settings.
    """
    # Parse the URL
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)

    # Ensure sslmode is set for Supabase
    if "sslmode" not in query_params:
        query_params["sslmode"] = ["require"]

    # Rebuild URL with sslmode
    new_query = urlencode(query_params, doseq=True)
    new_parsed = parsed._replace(query=new_query)
    clean_url = urlunparse(new_parsed)

    # Convert to psycopg2 format (remove asyncpg prefix if present)
    clean_url = clean_url.replace("postgresql+asyncpg://", "postgresql://")
    clean_url = clean_url.replace("postgres://", "postgresql://")

    # pgbouncer compatibility connect_args
    connect_args = {
        "options": "-c statement_timeout=30000"  # 30 second timeout
    }

    return clean_url, connect_args


# Prepare database URL
sync_database_url, _connect_args = _prepare_sync_database_url(settings.DATABASE_URL)

# Create synchronous engine
sync_engine = create_engine(
    sync_database_url,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    connect_args=_connect_args,
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
