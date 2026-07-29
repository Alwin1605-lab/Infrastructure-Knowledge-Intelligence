"""FastAPI Agents Endpoints — Phase 6 Agentic AI Pipeline.

Exposes the 5-agent Building Knowledge Intelligence pipeline through:

    POST /api/v1/agents/query          — Full multi-agent pipeline execution
    GET  /api/v1/agents/health         — Agent service health check
    GET  /api/v1/agents/pipeline/info  — Pipeline topology and configuration

All endpoints are 100% backward compatible with Phase 1–5.
Phase 5 /chat endpoints remain fully operational and untouched.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps import CurrentUserDep

from app.core.logging import get_logger
from app.schemas.agents import (
    AgentExecutionStepSchema,
    AgentPipelineRequest,
    AgentPipelineResponse,
)
from app.schemas.chat import ChatResponse
from app.services.agent_service import AgentService

logger = get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Dependency: AgentService from app.state
# ---------------------------------------------------------------------------

def get_agent_service(request: Request) -> AgentService:
    """Retrieve the AgentService singleton from application state."""
    service = getattr(request.app.state, "agent_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent pipeline is not initialized. Please check application startup logs.",
        )
    return service


AgentServiceDep = Annotated[AgentService, Depends(get_agent_service)]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/query",
    response_model=AgentPipelineResponse,
    summary="Multi-Agent Building Knowledge Query",
    description=(
        "Submit a building engineering question to the full 5-agent AI pipeline. "
        "Each agent has a single responsibility:\n\n"
        "1. **QueryAnalysisAgent** — Classifies intent, validates domain, extracts entities\n"
        "2. **RetrievalAgent** — Runs Hybrid RAG (ChromaDB + Neo4j)\n"
        "3. **KGReasoningAgent** — Multi-hop Knowledge Graph enrichment\n"
        "4. **RecommendationAgent** — Prioritized maintenance recommendations\n"
        "5. **ReportAgent** — Structured engineering assessment report\n\n"
        "Every agent in the execution trace reports:\n"
        "- **status** (success / skipped / failed)\n"
        "- **time_ms** (execution duration)\n"
        "- **confidence** (agent-specific confidence score 0.0–1.0)\n"
        "- **reason** (human-readable explanation of the agent's decision)\n\n"
        "**Domain**: RCC Buildings, Residential, Commercial, Institutional, Government structures only.\n"
        "**Stateless**: Each request is processed independently with no session memory."
    ),
    responses={
        200: {"description": "Successful multi-agent pipeline response"},
        503: {"description": "Agent pipeline not initialized"},
    },
)
async def run_agent_pipeline(
    request: AgentPipelineRequest,
    agent_service: AgentServiceDep,
    current_user: CurrentUserDep,
) -> AgentPipelineResponse:
    """Execute the full 5-agent pipeline for a building engineering query.

    **What you get back:**
    - `rag_response`: Full Phase 5 ChatResponse (answer, sources, KG context, confidence)
    - `report`: Structured engineering assessment report (Executive Summary, Component Assessment, Recommendations, Risk Matrix, References)
    - `execution_trace`: Per-agent diagnostics showing exactly what each agent decided and why
    - `overall_confidence`: Weighted average of all agent confidence scores

    **Example question:** *"What causes spalling in RCC columns and how should it be repaired?"*
    """
    logger.info(
        "agent_query_received",
        question=request.question[:80],
        top_k=request.top_k,
        include_kg=request.include_kg,
    )

    try:
        raw_result = await agent_service.run(
            question=request.question,
            top_k=request.top_k,
            include_kg=request.include_kg,
        )

        # Convert execution trace dicts to AgentExecutionStepSchema objects
        trace_schemas = [
            AgentExecutionStepSchema(**step)
            for step in raw_result.get("execution_trace", [])
        ]

        response = AgentPipelineResponse(
            session_id=raw_result["session_id"],
            question=raw_result["question"],
            rag_response=raw_result.get("rag_response"),
            report=raw_result.get("report", ""),
            execution_trace=trace_schemas,
            total_agents_run=raw_result["total_agents_run"],
            total_pipeline_ms=raw_result["total_pipeline_ms"],
            pipeline_version=raw_result["pipeline_version"],
            overall_confidence=raw_result["overall_confidence"],
            domain_valid=raw_result.get("domain_valid", True),
            query_intent=raw_result.get("query_intent"),
            enriched_kg_available=raw_result.get("enriched_kg_available", False),
        )

        logger.info(
            "agent_query_complete",
            session_id=response.session_id,
            total_ms=response.total_pipeline_ms,
            agents_run=response.total_agents_run,
            confidence=response.overall_confidence,
        )

        return response

    except Exception as exc:
        logger.error("agent_query_failed", error=str(exc), question=request.question[:80])
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent pipeline error: {exc}",
        ) from exc


@router.get(
    "/health",
    summary="Agent Pipeline Health Check",
    description="Verify that the 5-agent pipeline is initialized and all components are operational.",
)
async def agent_health(agent_service: AgentServiceDep, current_user: CurrentUserDep) -> dict:
    """Return the health status of the Agent pipeline and its components."""
    return await agent_service.health()


@router.get(
    "/pipeline/info",
    summary="Agent Pipeline Configuration",
    description=(
        "Returns the full pipeline topology: agent names, their responsibilities, "
        "execution order, retry policy, and system configuration."
    ),
)
async def pipeline_info(request: Request, current_user: CurrentUserDep) -> dict:
    """Return the agent pipeline configuration for transparency and debugging."""
    from app.config import get_settings
    settings = get_settings()

    return {
        "pipeline_name": "AgentOrchestrator",
        "version": "6.0",
        "domain": "Buildings Only — RCC, Residential, Commercial, Institutional, Government",
        "stateless": True,
        "session_memory": False,
        "agents": [
            {
                "order": 1,
                "name": "QueryAnalysisAgent",
                "responsibility": "Intent classification, domain validation, entity extraction, query reformulation",
                "llm_call": True,
                "fallback": "Regex-only QueryProcessor if LLM fails",
            },
            {
                "order": 2,
                "name": "RetrievalAgent",
                "responsibility": "Hybrid RAG — ChromaDB semantic search + Neo4j KG retrieval",
                "llm_call": False,
                "retries": 2,
            },
            {
                "order": 3,
                "name": "KGReasoningAgent",
                "responsibility": "Multi-hop KG traversal: defect → cause → repair → standard chains",
                "llm_call": False,
                "skipped_when": "include_kg=False or no entities extracted",
            },
            {
                "order": 4,
                "name": "RecommendationAgent",
                "responsibility": "Prioritized maintenance and repair recommendations with source references",
                "llm_call": True,
                "retries": 2,
            },
            {
                "order": 5,
                "name": "ReportAgent",
                "responsibility": "Structured engineering report (Executive Summary, Component Assessment, Risk Matrix, References)",
                "llm_call": True,
            },
        ],
        "routing": {
            "domain_rejection": "All downstream agents skipped if QueryAnalysisAgent rejects query",
            "kg_skip": "KGReasoningAgent skipped if include_kg=False or no entities extracted",
            "error_handling": "Failed agents recorded in trace, pipeline continues with best available state",
        },
        "models": {
            "llm": settings.GROQ_MODEL,
            "embedding": settings.EMBEDDING_MODEL,
            "llm_provider": settings.LLM_PROVIDER,
        },
        "phase5_compatibility": "POST /api/v1/chat/query fully preserved and unchanged",
    }
