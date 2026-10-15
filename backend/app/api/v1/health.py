import psutil
from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(prefix="/health", tags=["System Health"])

class SystemHealthResponse(BaseModel):
    status: str
    versions: dict
    services: dict
    system_metrics: dict
    knowledge_base: dict
    queue_stats: dict

@router.get("/system", response_model=SystemHealthResponse)
async def get_system_health(request: Request):
    """Retrieve comprehensive system health and versions."""
    
    # 1. Versions
    versions = {
        "backend_version": "0.9.0",
        "api_version": "v1",
        "pipeline_version": "Agentic-v2",
        "frontend_version": "0.8.0",
        "kb_version": "v1.0"
    }

    # 2. Services
    services = {
        "mongodb": "down",
        "neo4j": "down",
        "chromadb": "down",
        "groq_llm": "down"
    }

    # Check MongoDB
    try:
        from app.models.document import Document
        # Just ping DB to check if it's up
        if await Document.find_all().limit(1).to_list() is not None:
            services["mongodb"] = "ok"
    except Exception:
        pass

    # Check Neo4j
    from app.knowledge_graph.connection import get_neo4j_driver
    try:
        driver = get_neo4j_driver()
        if driver:
            services["neo4j"] = "ok"
    except Exception:
        pass

    # Check ChromaDB
    if getattr(request.app.state, "chroma_client", None) is not None:
        services["chromadb"] = "ok"

    # Check LLM
    if getattr(request.app.state, "llm_provider", None) is not None:
        services["groq_llm"] = "ok"

    # 3. Knowledge Base Stats
    kb_stats = {
        "documents_indexed": 0,
        "kg_nodes": 0,
        "kg_relationships": 0,
        "chroma_chunks": 0
    }

    if services["mongodb"] == "ok":
        try:
            from app.models.document import Document
            kb_stats["documents_indexed"] = await Document.count()
        except Exception:
            pass
            
    if services["chromadb"] == "ok":
        try:
            client = getattr(request.app.state, "chroma_client", None)
            if client:
                col = await client.get_or_create_collection("infrastructure_knowledge")
                kb_stats["chroma_chunks"] = await col.count()
        except Exception:
            pass
            
    if services["neo4j"] == "ok":
        try:
            async with get_neo4j_driver().session() as session:
                result = await session.run("MATCH (n) RETURN count(n) as node_count")
                record = await result.single()
                kb_stats["kg_nodes"] = record["node_count"]
                
                result = await session.run("MATCH ()-[r]->() RETURN count(r) as rel_count")
                record = await result.single()
                kb_stats["kg_relationships"] = record["rel_count"]
        except Exception:
            pass

    # 4. System Metrics
    system_metrics = {
        "memory_percent": psutil.virtual_memory().percent,
        "cpu_percent": psutil.cpu_percent(interval=None)
    }
    
    # 5. Queue Stats
    try:
        from app.services.analytics_service import AnalyticsService
        svc = AnalyticsService()
        queue_stats = await svc.get_processing_queue_stats()
    except Exception:
        queue_stats = {}

    overall_status = "ok" if all(v == "ok" for v in services.values()) else "degraded"

    return SystemHealthResponse(
        status=overall_status,
        versions=versions,
        services=services,
        system_metrics=system_metrics,
        knowledge_base=kb_stats,
        queue_stats=queue_stats
    )
