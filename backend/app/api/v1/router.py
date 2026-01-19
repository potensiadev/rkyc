"""
rKYC API v1 Router
Aggregates all API endpoints
"""

from fastapi import APIRouter
from app.api.v1.endpoints import corporations, signals, jobs, dashboard, documents, profiles, admin

# Create main API router
api_router = APIRouter()

# Include endpoint routers
api_router.include_router(
    corporations.router, prefix="/corporations", tags=["corporations"]
)
api_router.include_router(signals.router, prefix="/signals", tags=["signals"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(profiles.router, tags=["profiles"])  # Routes: /corporations/{corp_id}/profile*
api_router.include_router(admin.router, tags=["admin"])  # PRD v1.2: Circuit Breaker Status API
