"""
rKYC API v1 Router
Aggregates all API endpoints
"""

from fastapi import APIRouter
from app.api.v1.endpoints import corporations, signals, jobs, dashboard, documents, profiles, admin, signals_enriched, scheduler, diagnostics, reports, loan_insights, dart
# from app.api.v1.endpoints import new_kyc  # 신규 법인 KYC - 비활성화

# Create main API router
api_router = APIRouter()

# Include endpoint routers
api_router.include_router(
    corporations.router, prefix="/corporations", tags=["corporations"]
)
api_router.include_router(signals.router, prefix="/signals", tags=["signals"])
api_router.include_router(signals_enriched.router, prefix="/signals-enriched", tags=["signals-enriched"])  # Enriched signal detail (separate prefix to avoid collision)
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(profiles.router, tags=["profiles"])  # Routes: /corporations/{corp_id}/profile*
api_router.include_router(admin.router, tags=["admin"])  # PRD v1.2: Circuit Breaker Status API
# api_router.include_router(new_kyc.router, prefix="/new-kyc", tags=["new-kyc"])  # 신규 법인 KYC - 비활성화
api_router.include_router(scheduler.router, prefix="/scheduler", tags=["scheduler"])  # Real-time signal detection control
api_router.include_router(diagnostics.router, prefix="/diagnostics", tags=["diagnostics"])  # Pipeline diagnostics
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])  # Full reports with evidence
api_router.include_router(loan_insights.router, prefix="/loan-insights", tags=["loan-insights"])  # Pre-generated Loan Insight
api_router.include_router(dart.router, prefix="/dart", tags=["dart"])  # DART 주주 정보 검증 API
