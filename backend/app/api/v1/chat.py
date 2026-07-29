"""FastAPI Chat Endpoints — Phase 5 Hybrid RAG Pipeline.

Exposes the Building Knowledge Intelligence Q&A system through the following endpoints:

    POST /api/v1/chat/query         — Full structured RAG query with 7-field response
    POST /api/v1/chat/query/stream  — Server-Sent Events streaming for real-time display
    GET  /api/v1/chat/health        — Pipeline health check
    GET  /api/v1/chat/pipeline/info — Pipeline configuration info

All endpoints use the RAGService injected from app.state (initialized at startup).
The ChatRequest and ChatResponse schemas are from app/schemas/chat.py — unchanged.
"""

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.api.deps import LLMProviderDep, EmbeddingServiceDep, SettingsDep
from app.core.logging import get_logger
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.rag_service import RAGService

logger = get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Dependency: RAGService from app.state
# ---------------------------------------------------------------------------

def get_rag_service(request: Request) -> RAGService:
    """Retrieve the RAGService singleton from application state."""
    rag_service = getattr(request.app.state, "rag_service", None)
    if rag_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG pipeline is not initialized. Please check application startup logs.",
        )
    return rag_service


RAGServiceDep = Annotated[RAGService, Depends(get_rag_service)]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/query",
    response_model=ChatResponse,
    summary="Query the Building Knowledge AI",
    description=(
        "Submit a natural language question about building engineering, "
        "structural assessment, defects, maintenance, or rehabilitation. "
        "Returns a fully structured response with source citations, "
        "Knowledge Graph context, confidence score, and engineering recommendations. "
        "\n\n**Domain**: RCC Buildings, Residential, Commercial, Institutional, Government structures only."
    ),
    responses={
        200: {"description": "Successful structured AI response"},
        400: {"description": "Query is outside the building engineering domain"},
        503: {"description": "RAG pipeline not initialized"},
    },
)
async def query_building_knowledge(
    request: ChatRequest,
    rag_service: RAGServiceDep,
) -> ChatResponse:
    """Execute a hybrid RAG query against the building knowledge base.

    **Pipeline stages (transparent to the caller):**
    1. Query preprocessing and domain validation
    2. Semantic vector search (ChromaDB)
    3. Knowledge Graph traversal (Neo4j)
    4. Chunk reranking
    5. Context fusion
    6. Groq LLM answer generation
    7. Confidence scoring
    8. Structured response assembly

    **Response fields:**
    - `answer`: AI-generated technically precise answer
    - `sources`: Cited documents with page and section references
    - `kg_context`: Relevant building entities from the Knowledge Graph
    - `confidence`: Score, level, grounding type, and reasoning
    - `recommendations`: Prioritized engineering action items
    - `related_components`: Connected building structural elements
    - `response_time`: Per-stage timing breakdown

    **Example question:** *"What causes spalling in RCC columns and how should it be repaired?"*
    """
    logger.info("chat_query_received", question=request.question[:80], top_k=request.top_k)

    try:
        response = await rag_service.query(request)
        logger.info(
            "chat_query_complete",
            confidence=response.confidence.score,
            grounding=response.confidence.grounding,
            sources=len(response.sources),
            total_ms=response.response_time.total_ms,
        )
        return response

    except Exception as exc:
        logger.error("chat_query_failed", error=str(exc), question=request.question[:80])
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG pipeline error: {exc}",
        ) from exc


@router.post(
    "/query/stream",
    summary="Stream a Building Knowledge AI response (SSE)",
    description=(
        "Same as `/query` but streams the LLM response as Server-Sent Events (SSE). "
        "Useful for real-time chat interfaces. Each SSE event is a JSON object with a "
        "`chunk` field containing streamed text. A final `[DONE]` event is sent when complete."
    ),
    responses={
        200: {"content": {"text/event-stream": {}}},
        503: {"description": "RAG pipeline not initialized"},
    },
)
async def stream_building_knowledge(
    request: ChatRequest,
    rag_service: RAGServiceDep,
    llm_provider: LLMProviderDep,
    embedding_service: EmbeddingServiceDep,
) -> StreamingResponse:
    """Stream an AI response for a building engineering query.

    Uses Server-Sent Events (SSE) to stream the LLM's response in real time.
    Retrieval and KG lookup are completed before streaming begins.
    """
    from app.rag.pipeline import HybridRAGPipeline
    from app.rag.query_processor import QueryProcessor
    from app.rag.context_fusion import ContextFuser
    from app.rag.reranker import ChunkReranker
    from app.knowledge_graph.queries import get_defect_subgraph, get_component_subgraph, search_entities_by_text
    from app.prompts.rag import RAGPrompts
    from app.vectorstore.retriever import ChromaRetriever
    from app.config import get_settings

    settings = get_settings()
    retriever = ChromaRetriever(embedding_service=embedding_service, similarity_threshold=settings.RAG_SIMILARITY_THRESHOLD)

    async def event_generator():
        try:
            # Run preprocessing + retrieval + KG synchronously first
            processor = QueryProcessor()
            processed = processor.preprocess(request.question)

            if not processed.is_building_domain:
                yield f"data: {json.dumps({'chunk': processed.rejection_reason})}\n\n"
                yield "data: [DONE]\n\n"
                return

            raw_chunks = await retriever.retrieve(processed.expanded_query, top_k=request.top_k)
            reranker = ChunkReranker()
            ranked = reranker.rerank(raw_chunks, processed)

            # KG traversal
            kg_subgraphs = []
            for defect in processed.extracted_defects[:2]:
                sg = await get_defect_subgraph(defect)
                if sg:
                    kg_subgraphs.append(sg)
            if not kg_subgraphs and processed.kg_search_terms:
                entities = await search_entities_by_text(processed.kg_search_terms[0], limit=8)
                if entities:
                    kg_subgraphs.append({"entities": entities, "relationships": []})

            fuser = ContextFuser()
            fused = fuser.fuse(ranked_chunks=ranked, kg_subgraphs=kg_subgraphs, question=request.question)

            # Stream LLM response
            async for chunk_text in llm_provider.generate_stream(
                prompt=fused.full_prompt,
                system_prompt=RAGPrompts.SYSTEM_PROMPT,
            ):
                yield f"data: {json.dumps({'chunk': chunk_text})}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as exc:
            logger.error("stream_query_failed", error=str(exc))
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/health",
    summary="RAG Pipeline Health Check",
    description="Verify that the RAG pipeline is initialized and all components are operational.",
)
async def rag_health_check(rag_service: RAGServiceDep) -> dict:
    """Return the health status of the RAG pipeline and its sub-components."""
    return await rag_service.health()


@router.get(
    "/pipeline/info",
    summary="RAG Pipeline Configuration",
    description="Returns the pipeline configuration: stages, models, thresholds, and domain info.",
)
async def pipeline_info(settings: SettingsDep) -> dict:
    """Return pipeline configuration metadata for transparency and debugging."""
    return {
        "pipeline_name": "HybridRAGPipeline",
        "version": "5.0",
        "domain": "Buildings Only — RCC, Residential, Commercial, Institutional, Government",
        "stages": {
            "1_query_processing": "Domain guard + entity extraction + query expansion",
            "2_vector_retrieval": f"ChromaDB semantic search (top_k configurable, threshold={settings.RAG_SIMILARITY_THRESHOLD})",
            "3_kg_traversal": "Neo4j defect/component subgraph traversal",
            "4_reranking": "Keyword-entity boosted chunk reranking",
            "5_context_fusion": "RAG prompt construction from chunks + KG",
            "6_llm_generation": f"Groq {settings.GROQ_MODEL} answer generation",
            "7_confidence_scoring": "Evidence-based confidence and grounding assessment",
            "8_response_assembly": "Typed ChatResponse construction with citations",
        },
        "models": {
            "embedding": settings.EMBEDDING_MODEL,
            "llm": settings.GROQ_MODEL,
            "llm_provider": settings.LLM_PROVIDER,
        },
        "vector_store": {
            "provider": "ChromaDB",
            "collection": settings.CHROMADB_COLLECTION,
            "similarity_threshold": settings.RAG_SIMILARITY_THRESHOLD,
        },
        "knowledge_graph": {
            "provider": "Neo4j",
            "uri": settings.NEO4J_URI,
        },
    }
