"""FastAPI dependency injection.

Provides shared dependencies (LLM provider, embedding service, settings,
ChromaDB indexer, ChromaDB retriever) to route handlers via Depends().

Usage in route handlers::

    @router.get("/example")
    async def example_route(
        llm: LLMProviderDep,
        embeddings: EmbeddingServiceDep,
        settings: SettingsDep,
        retriever: ChromaRetrieverDep,
    ):
        ...
"""

from typing import Annotated

from fastapi import Depends, Request

from app.config import Settings, get_settings
from app.llm.base import BaseLLMProvider
from app.embedding.huggingface import HuggingFaceEmbeddingService
from app.vectorstore.indexer import ChromaIndexer
from app.vectorstore.retriever import ChromaRetriever
from app.knowledge_graph.builder import KGBuilder


def get_llm_provider(request: Request) -> BaseLLMProvider:
    """Get the LLM provider from app state."""
    return request.app.state.llm_provider


def get_embedding_service(request: Request) -> HuggingFaceEmbeddingService:
    """Get the embedding service from app state."""
    return request.app.state.embedding_service


def get_chroma_indexer(request: Request) -> ChromaIndexer:
    """Get a ChromaDB indexer bound to the app's embedding service.

    Creates a new ChromaIndexer per request (lightweight — just holds
    a reference to the shared embedding service).
    """
    embedding_service = request.app.state.embedding_service
    return ChromaIndexer(embedding_service=embedding_service)


def get_chroma_retriever(request: Request) -> ChromaRetriever:
    """Get a ChromaDB retriever bound to the app's embedding service."""
    embedding_service = request.app.state.embedding_service
    settings = get_settings()
    return ChromaRetriever(
        embedding_service=embedding_service,
        similarity_threshold=settings.RAG_SIMILARITY_THRESHOLD,
    )


def get_kg_builder(request: Request) -> KGBuilder:
    """Get a Knowledge Graph builder bound to the app's LLM provider."""
    llm_provider = request.app.state.llm_provider
    return KGBuilder(llm_provider=llm_provider)


# Type aliases for cleaner route signatures
SettingsDep = Annotated[Settings, Depends(get_settings)]
LLMProviderDep = Annotated[BaseLLMProvider, Depends(get_llm_provider)]
EmbeddingServiceDep = Annotated[HuggingFaceEmbeddingService, Depends(get_embedding_service)]
ChromaIndexerDep = Annotated[ChromaIndexer, Depends(get_chroma_indexer)]
ChromaRetrieverDep = Annotated[ChromaRetriever, Depends(get_chroma_retriever)]
KGBuilderDep = Annotated[KGBuilder, Depends(get_kg_builder)]
