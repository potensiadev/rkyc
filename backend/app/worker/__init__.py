# Celery Worker Module
# P0 Fix: Lazy import to prevent psycopg2 dependency on module access
# This allows importing submodules (e.g., app.worker.llm) without DB driver

def __getattr__(name):
    """Lazy import celery_app only when explicitly accessed."""
    if name == "celery_app":
        from app.worker.celery_app import celery_app
        return celery_app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["celery_app"]
