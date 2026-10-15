"""Analytics API endpoints."""
from fastapi import APIRouter, Query
from app.api.deps import CurrentUserDep
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/kb")
async def get_kb_analytics(current_user: CurrentUserDep):
    """Get knowledge base statistics and growth data."""
    svc = AnalyticsService()
    stats = await svc.get_kb_stats()
    growth = await svc.get_kb_growth(days=30)
    queue = await svc.get_processing_queue_stats()
    return {"stats": stats, "growth": growth, "queue": queue}

@router.get("/queries")
async def get_query_analytics(current_user: CurrentUserDep):
    """Get query performance metrics."""
    svc = AnalyticsService()
    return await svc.get_query_metrics_summary()
