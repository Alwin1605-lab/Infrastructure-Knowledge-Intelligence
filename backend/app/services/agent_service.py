"""Agent Service Layer — Phase 6.

Thin wrapper around AgentOrchestrator for FastAPI dependency injection.
Initialized once at application startup and stored in app.state.agent_service.

This layer exists so that:
    1. Route handlers depend on AgentService, not directly on AgentOrchestrator.
    2. Mock injection for tests is trivial.
    3. Future telemetry, rate limiting, or caching can be added without
       touching orchestrator or agent logic.
"""

from typing import Any

from app.agents.orchestrator import AgentOrchestrator
from app.core.logging import get_logger
from app.embedding.huggingface import HuggingFaceEmbeddingService
from app.llm.base import BaseLLMProvider
from app.rag.pipeline import HybridRAGPipeline
from app.vectorstore.retriever import ChromaRetriever
from app.config import get_settings

logger = get_logger(__name__)


class AgentService:
    """Service wrapper for the multi-agent orchestration pipeline.

    Owns a single AgentOrchestrator instance which is reused across all
    requests. Each request gets a fresh stateless AgentState.

    Args:
        llm_provider: Active LLM provider.
        embedding_service: HuggingFace embedding service.
    """

    def __init__(
        self,
        llm_provider: BaseLLMProvider,
        embedding_service: HuggingFaceEmbeddingService,
    ) -> None:
        settings = get_settings()
        retriever = ChromaRetriever(
            embedding_service=embedding_service,
            similarity_threshold=settings.RAG_SIMILARITY_THRESHOLD,
        )
        rag_pipeline = HybridRAGPipeline(
            llm_provider=llm_provider,
            embedding_service=embedding_service,
            retriever=retriever,
        )
        self._orchestrator = AgentOrchestrator(
            llm_provider=llm_provider,
            rag_pipeline=rag_pipeline,
        )
        logger.info("agent_service_initialized")

    async def run(
        self,
        question: str,
        top_k: int = 5,
        include_kg: bool = True,
    ) -> dict[str, Any]:
        """Execute the full agent pipeline for a user query.

        Args:
            question: The user's building engineering question.
            top_k: Number of RAG chunks to retrieve.
            include_kg: Whether to run KG Reasoning Agent.

        Returns:
            dict: AgentPipelineResponse-compatible dictionary.
        """
        return await self._orchestrator.run(
            question=question,
            top_k=top_k,
            include_kg=include_kg,
        )

    async def health(self) -> dict[str, Any]:
        """Return service and orchestrator health status."""
        orchestrator_health = await self._orchestrator.health()
        return {
            "service": "AgentService",
            "status": "healthy",
            **orchestrator_health,
        }
