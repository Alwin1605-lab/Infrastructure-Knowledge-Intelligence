"""API v1 aggregated router.

Mounts all v1 sub-routers and provides health check endpoints.
The health endpoints allow monitoring of individual components
(LLM, embedding) as well as full system health.

Endpoints:
    GET /health          - Basic liveness check
    GET /health/llm      - LLM provider connectivity check
    GET /health/embedding - Embedding service health check
    GET /health/full     - Aggregated system health with all components
"""

from fastapi import APIRouter, Depends

from app.config import get_settings, Settings
from app.api.deps import LLMProviderDep, EmbeddingServiceDep

api_v1_router = APIRouter(tags=["v1"])


@api_v1_router.get("/health")
async def health_check():
    """Basic health check.

    Returns a simple healthy status to confirm the API is reachable.
    This endpoint has no dependencies and will succeed as long as the
    application is running.

    Returns:
        dict: Health status with service name.
    """
    return {"status": "healthy", "service": "Infrastructure Knowledge Intelligence"}


@api_v1_router.get("/health/llm")
async def llm_health_check(llm_provider: LLMProviderDep):
    """Check LLM provider health and connectivity.

    Delegates to the LLM provider's own health_check method to verify
    that the provider API is reachable and properly configured.

    Args:
        llm_provider: The active LLM provider instance (injected).

    Returns:
        dict: Health status from the LLM provider.
    """
    result = await llm_provider.health_check()
    return result


@api_v1_router.get("/health/embedding")
async def embedding_health_check(embedding_service: EmbeddingServiceDep):
    """Check embedding service health.

    Verifies that the embedding model is loaded and operational.

    Args:
        embedding_service: The active embedding service (injected).

    Returns:
        dict: Health status from the embedding service.
    """
    result = await embedding_service.health_check()
    return result


@api_v1_router.get("/health/full")
async def full_health_check(
    llm_provider: LLMProviderDep,
    embedding_service: EmbeddingServiceDep,
    settings: Settings = Depends(get_settings),
):
    """Full system health check.

    Aggregates health status from all system components (LLM provider,
    embedding service) into a single response. Useful for monitoring
    dashboards and deployment readiness checks.

    Args:
        llm_provider: The active LLM provider instance (injected).
        embedding_service: The active embedding service (injected).
        settings: Application settings (injected).

    Returns:
        dict: Aggregated health status with per-component details.
    """
    llm_status = await llm_provider.health_check()
    embedding_status = await embedding_service.health_check()

    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "components": {
            "llm": llm_status,
            "embedding": embedding_status,
        },
    }


# --- Mount sub-routers ---
from app.api.v1 import documents, knowledge_graph
api_v1_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
api_v1_router.include_router(knowledge_graph.router, prefix="/kg", tags=["Knowledge Graph"])

# Future routers:
# from app.api.v1 import chat, agents, reports
# api_v1_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
# api_v1_router.include_router(agents.router, prefix="/agents", tags=["Agents"])
# api_v1_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
