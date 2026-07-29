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

from fastapi import APIRouter

from app.api.v1.health import router as health_router

api_v1_router = APIRouter(tags=["v1"])

api_v1_router.include_router(health_router)


# --- Mount sub-routers ---
from app.api.v1 import auth, workspaces, workspace_documents, documents, knowledge_graph, chat, agents, evaluation, activity
api_v1_router.include_router(auth.router)
api_v1_router.include_router(workspaces.router)
api_v1_router.include_router(workspace_documents.router)
api_v1_router.include_router(activity.router)
api_v1_router.include_router(documents.router, prefix="/documents", tags=["Global Documents"])
api_v1_router.include_router(knowledge_graph.router, prefix="/kg", tags=["Knowledge Graph"])
api_v1_router.include_router(chat.router, prefix="/chat", tags=["Chat — Hybrid RAG Pipeline"])
api_v1_router.include_router(agents.router, prefix="/agents", tags=["Agents — Agentic AI Pipeline"])
api_v1_router.include_router(evaluation.router, prefix="/eval", tags=["Evaluation — Phase 7"])

# Future routers (Phase 8+):
# from app.api.v1 import reports
# api_v1_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
