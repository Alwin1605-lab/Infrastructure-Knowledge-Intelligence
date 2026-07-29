"""RAG Service Layer.

Thin service wrapper around HybridRAGPipeline for injection via FastAPI dependencies.
Initialized once at application startup and stored in `app.state.rag_service`.

This layer exists so that:
    1. Route handlers depend on RAGService, not directly on HybridRAGPipeline.
    2. Mocking for tests is straightforward.
    3. Future batch-query or caching logic can be added here without touching the pipeline.
"""

from app.core.logging import get_logger
from app.embedding.huggingface import HuggingFaceEmbeddingService
from app.llm.base import BaseLLMProvider
from app.rag.pipeline import HybridRAGPipeline
from app.schemas.chat import ChatRequest, ChatResponse
from app.vectorstore.retriever import ChromaRetriever
from app.config import get_settings

logger = get_logger(__name__)


class RAGService:
    """Service wrapper for the Hybrid RAG Pipeline.

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
        self._pipeline = HybridRAGPipeline(
            llm_provider=llm_provider,
            embedding_service=embedding_service,
            retriever=retriever,
        )
        logger.info(
            "rag_service_initialized",
            llm=llm_provider.provider_name,
            embedding="all-MiniLM-L6-v2",
        )

    async def query(self, request: ChatRequest) -> ChatResponse:
        """Execute the full hybrid RAG pipeline for a user query.

        Args:
            request: Validated ChatRequest.

        Returns:
            ChatResponse: Complete structured response.
        """
        return await self._pipeline.query(request)

    async def health(self) -> dict:
        """Return pipeline health status."""
        return {
            "status": "healthy",
            "pipeline": "HybridRAGPipeline",
            "stages": [
                "QueryProcessor",
                "ChromaRetriever",
                "KGTraversal",
                "ChunkReranker",
                "ContextFuser",
                "GroqLLM",
                "ConfidenceScorer",
                "ResponseParser",
            ],
            "llm": self._pipeline._llm.provider_name,
            "embedding_model": "all-MiniLM-L6-v2",
        }
