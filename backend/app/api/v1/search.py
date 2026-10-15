"""Global Search API endpoints."""
from fastapi import APIRouter, Query
from typing import Optional
from app.api.deps import CurrentUserDep
from app.services.search_service import SearchService

router = APIRouter(prefix="/search", tags=["Global Search"])

@router.get("")
async def global_search(
    current_user: CurrentUserDep,
    q: str = Query(..., min_length=1),
    document_type: Optional[str] = Query(default=None),
    workspace_id: Optional[str] = Query(default=None),
    limit: int = Query(default=20, le=50),
):
    """Search across all platform data."""
    svc = SearchService()
    results = await svc.search(
        query=q,
        document_type=document_type,
        workspace_id=workspace_id,
        limit=limit,
        user_id=str(current_user.id),
    )
    return {"results": results, "query": q, "total": len(results)}

@router.get("/suggestions")
async def get_suggestions(
    current_user: CurrentUserDep,
    q: str = Query(..., min_length=2),
    limit: int = Query(default=8, le=20),
):
    """Get search autocomplete suggestions."""
    svc = SearchService()
    suggestions = await svc.get_suggestions(query=q, limit=limit)
    return {"suggestions": suggestions}
