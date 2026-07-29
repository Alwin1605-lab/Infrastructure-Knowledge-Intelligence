"""Hybrid RAG Pipeline — Main Orchestrator (Phase 5).

Wires together QueryProcessor → ChromaRetriever → KG Traversal → ChunkReranker
→ ContextFuser → Groq LLM → ConfidenceScorer → ResponseParser into a single
async `query()` call.

Design principles:
    - Each stage is independently testable and has a single responsibility.
    - KG failure is non-fatal: the pipeline falls back to rag_only gracefully.
    - All timing is measured with nanosecond precision from time.perf_counter_ns().
    - The pipeline holds no mutable state between requests (fully stateless).
    - Uses only existing services — no new DB calls or network dependencies.

Domain: Buildings Only (RCC, Residential, Commercial, Institutional, Government).
"""

import time
from typing import TYPE_CHECKING, Any

from app.core.logging import get_logger
from app.core.exceptions import RAGError, RetrievalError
from app.knowledge_graph.queries import (
    get_defect_subgraph,
    get_component_subgraph,
    search_entities_by_text,
)
from app.prompts.rag import RAGPrompts
from app.rag.confidence import ConfidenceScorer
from app.rag.context_fusion import ContextFuser
from app.rag.query_processor import QueryProcessor
from app.rag.reranker import ChunkReranker
from app.rag.response_parser import ResponseParser
from app.schemas.chat import ChatRequest, ChatResponse, ConfidenceScore, ResponseTime

if TYPE_CHECKING:
    from app.embedding.huggingface import HuggingFaceEmbeddingService
    from app.llm.base import BaseLLMProvider
    from app.vectorstore.retriever import ChromaRetriever

logger = get_logger(__name__)


class HybridRAGPipeline:
    """End-to-end Hybrid RAG Pipeline for the Building Knowledge Intelligence System.

    Combines:
        - Semantic vector search (ChromaDB + all-MiniLM-L6-v2)
        - Structured graph traversal (Neo4j Knowledge Graph)
        - Grounded answer generation (Groq llama-3.1-8b-instant)

    Args:
        llm_provider: Active LLM provider (Groq or Ollama).
        embedding_service: HuggingFace embedding service for query vectorization.
        retriever: ChromaDB retriever for semantic search.
        similarity_threshold: Minimum cosine similarity score for vector retrieval.

    Example:
        >>> pipeline = HybridRAGPipeline(llm_provider, embedding_service, retriever)
        >>> request = ChatRequest(question="What causes spalling?", top_k=5)
        >>> response = await pipeline.query(request)
        >>> print(response.answer)
    """

    def __init__(
        self,
        llm_provider: "BaseLLMProvider",
        embedding_service: "HuggingFaceEmbeddingService",
        retriever: "ChromaRetriever",
    ) -> None:
        self._llm = llm_provider
        self._embedding_service = embedding_service
        self._retriever = retriever

        # Sub-components (all stateless)
        self._query_processor = QueryProcessor()
        self._reranker = ChunkReranker(min_final_score=0.18)
        self._context_fuser = ContextFuser()
        self._confidence_scorer = ConfidenceScorer()

    async def query(self, request: ChatRequest) -> ChatResponse:
        """Execute the full 8-stage hybrid RAG pipeline for a user query.

        Args:
            request: Validated ChatRequest with question, top_k, include_kg_context flags.

        Returns:
            ChatResponse: Complete structured response with answer, sources, KG context,
                          confidence, recommendations, related components, and timings.

        Raises:
            RAGError: If a critical unrecoverable error occurs in the pipeline.
        """
        pipeline_start_ns = time.perf_counter_ns()
        logger.info("rag_pipeline_start", question=request.question[:80])

        # -----------------------------------------------------------------------
        # STAGE 1: Query Preprocessing
        # -----------------------------------------------------------------------
        processed_query = self._query_processor.preprocess(request.question)

        if not processed_query.is_building_domain:
            return self._build_rejection_response(
                request=request,
                reason=processed_query.rejection_reason or "Query is outside the building domain.",
                start_ns=pipeline_start_ns,
            )

        # -----------------------------------------------------------------------
        # STAGE 2: Vector Retrieval (ChromaDB)
        # -----------------------------------------------------------------------
        retrieval_start_ns = time.perf_counter_ns()
        try:
            raw_chunks = await self._retriever.retrieve(
                query=processed_query.expanded_query,
                top_k=request.top_k,
            )
        except RetrievalError as exc:
            logger.warning("vector_retrieval_failed", error=str(exc))
            raw_chunks = []
        retrieval_ms = (time.perf_counter_ns() - retrieval_start_ns) / 1_000_000

        # -----------------------------------------------------------------------
        # STAGE 3: Knowledge Graph Traversal
        # -----------------------------------------------------------------------
        kg_start_ns = time.perf_counter_ns()
        kg_subgraphs: list[dict[str, Any]] = []

        if request.include_kg_context:
            try:
                # Run defect subgraph queries for each extracted defect
                for defect in processed_query.extracted_defects[:3]:
                    sg = await get_defect_subgraph(defect)
                    if sg:
                        kg_subgraphs.append(sg)

                # Run component subgraph queries for each extracted component
                for component in processed_query.extracted_components[:2]:
                    sg = await get_component_subgraph(component)
                    if sg:
                        kg_subgraphs.append(sg)

                # General entity search for remaining KG terms
                if not kg_subgraphs and processed_query.kg_search_terms:
                    primary_term = processed_query.kg_search_terms[0]
                    entities = await search_entities_by_text(primary_term, limit=10)
                    if entities:
                        kg_subgraphs.append({"entities": entities, "relationships": []})

            except Exception as exc:
                # KG failure is non-fatal — pipeline continues with rag_only
                logger.warning("kg_traversal_failed_non_fatal", error=str(exc))
                kg_subgraphs = []

        kg_lookup_ms = (time.perf_counter_ns() - kg_start_ns) / 1_000_000

        # -----------------------------------------------------------------------
        # STAGE 4: Chunk Reranking
        # -----------------------------------------------------------------------
        ranked_chunks = self._reranker.rerank(raw_chunks, processed_query)

        # -----------------------------------------------------------------------
        # STAGE 5: Context Fusion
        # -----------------------------------------------------------------------
        fused_context = self._context_fuser.fuse(
            ranked_chunks=ranked_chunks,
            kg_subgraphs=kg_subgraphs,
            question=request.question,
        )

        # -----------------------------------------------------------------------
        # STAGE 6: LLM Generation (Groq)
        # -----------------------------------------------------------------------
        llm_start_ns = time.perf_counter_ns()

        if fused_context.has_sufficient_context:
            try:
                llm_response = await self._llm.generate(
                    prompt=fused_context.full_prompt,
                    system_prompt=RAGPrompts.SYSTEM_PROMPT,
                )
                llm_text = llm_response.content
            except Exception as exc:
                logger.error("llm_generation_failed", error=str(exc))
                llm_text = (
                    f"The AI model encountered an error while generating the response: {exc}. "
                    f"Retrieved context is available in the sources section."
                )
        else:
            llm_text = fused_context.full_prompt  # Already formatted as insufficient-context message

        # -----------------------------------------------------------------------
        # STAGE 7: Confidence Scoring
        # -----------------------------------------------------------------------
        confidence = self._confidence_scorer.score(
            ranked_chunks=ranked_chunks,
            num_kg_entities=fused_context.num_kg_entities,
            question=request.question,
        )

        # -----------------------------------------------------------------------
        # STAGE 8: Response Assembly
        # -----------------------------------------------------------------------
        parser = ResponseParser(
            start_time_ns=pipeline_start_ns,
            retrieval_ms=retrieval_ms,
            kg_lookup_ms=kg_lookup_ms,
            llm_start_ns=llm_start_ns,
        )

        response = parser.parse(
            llm_text=llm_text,
            ranked_chunks=ranked_chunks,
            kg_data=fused_context.raw_kg_data,
            confidence=confidence,
            question=request.question,
        )

        total_ms = (time.perf_counter_ns() - pipeline_start_ns) / 1_000_000
        logger.info(
            "rag_pipeline_complete",
            total_ms=round(total_ms, 1),
            sources=len(response.sources),
            kg_entities=len(response.kg_context),
            confidence=confidence.score,
            grounding=confidence.grounding,
        )

        return response

    def _build_rejection_response(
        self,
        request: ChatRequest,
        reason: str,
        start_ns: int,
    ) -> ChatResponse:
        """Build a polite rejection response for out-of-domain queries."""
        elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000

        return ChatResponse(
            answer=reason,
            sources=[],
            kg_context=[],
            confidence=ConfidenceScore(
                score=0.0,
                level="insufficient",
                grounding="insufficient_context",
                reasoning="Query is outside the building engineering domain.",
            ),
            recommendations=[],
            related_components=[],
            response_time=ResponseTime(
                total_ms=round(elapsed_ms, 1),
                retrieval_ms=0.0,
                kg_lookup_ms=0.0,
                llm_generation_ms=0.0,
                post_processing_ms=0.0,
            ),
        )
