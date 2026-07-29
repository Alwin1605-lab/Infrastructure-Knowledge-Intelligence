"""Knowledge Graph query API endpoints.

Provides REST endpoints for exploring the Building Knowledge Graph:
    - GET /kg/defect/{defect_name}          — Query defect root causes, repairs, affected components
    - GET /kg/component/{component_name}    — Query component defects, materials, system hierarchy
    - GET /kg/repairs/{defect_name}         — Query repair recommendations & standard citations
    - GET /kg/search                        — Search building entities by text
    - GET /kg/document/{document_id}        — Get all entities/relationships for a document
"""

from typing import Any, Optional
from fastapi import APIRouter, HTTPException, Query

from app.api.deps import CurrentUserDep
from app.core.exceptions import KGQueryError
from app.core.logging import get_logger
from app.knowledge_graph.queries import (
    get_defect_subgraph,
    get_component_subgraph,
    get_repair_recommendations_from_kg,
    search_entities_by_text,
    get_document_subgraph,
)

logger = get_logger(__name__)

router = APIRouter()


@router.get("/defect/{defect_name}", summary="Get defect root causes, repairs, and affected components")
async def query_defect(defect_name: str, current_user: CurrentUserDep) -> dict[str, Any]:
    """Retrieve all causes, repair methods, and affected building components for a defect."""
    try:
        data = await get_defect_subgraph(defect_name)
        if not data:
            return {"message": f"No defect found matching '{defect_name}' in the Building Knowledge Graph.", "defects_found": []}
        return data
    except KGQueryError as exc:
        raise HTTPException(status_code=500, detail=exc.message) from exc


@router.get("/component/{component_name}", summary="Get component details, defects, and materials")
async def query_component(component_name: str, current_user: CurrentUserDep) -> dict[str, Any]:
    """Retrieve building component subgraph including affecting defects and materials used."""
    data = await get_component_subgraph(component_name)
    if not data:
        return {"message": f"No component found matching '{component_name}' in the Building Knowledge Graph.", "components_found": []}
    return data


@router.get("/repairs/{defect_name}", summary="Get recommended repairs and standard citations")
async def query_repairs(
    defect_name: str,
    current_user: CurrentUserDep,
    component_name: Optional[str] = Query(None, description="Optional building component filter"),
) -> list[dict[str, Any]]:
    """Retrieve repair recommendations and standard citations for a defect."""
    repairs = await get_repair_recommendations_from_kg(defect_name, component_name)
    return repairs


@router.get("/search", summary="Search building entities by name across all types")
async def search_entities(
    current_user: CurrentUserDep,
    query: str = Query(..., min_length=2, description="Substring to search across entity names"),
    limit: int = Query(15, ge=1, le=50, description="Maximum number of results"),
) -> list[dict[str, Any]]:
    """Search for building entities across all labels matching a query string."""
    results = await search_entities_by_text(query=query, limit=limit)
    return results


@router.get("/document/{document_id}", summary="Get all entities and relationships extracted from a document")
async def query_document_graph(document_id: str, current_user: CurrentUserDep) -> dict[str, Any]:
    """Retrieve the document subgraph containing all entities and relationships extracted from this document."""
    subgraph = await get_document_subgraph(document_id)
    return subgraph
