"""
rKYC API v1 Router
Aggregates all API endpoints
"""

from fastapi import APIRouter
from app.api.v1.endpoints import corporations, signals

# Create main API router
api_router = APIRouter()

# Include endpoint routers
api_router.include_router(
    corporations.router, prefix="/corporations", tags=["corporations"]
)
api_router.include_router(signals.router, prefix="/signals", tags=["signals"])

# Note: analysis endpoint will be implemented later with Worker integration
