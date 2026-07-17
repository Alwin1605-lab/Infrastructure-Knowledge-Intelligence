"""Embedding Service Module.

Provides local embedding generation using HuggingFace sentence-transformers.
Always uses all-MiniLM-L6-v2. No API keys required.

Usage:
    from app.embedding import HuggingFaceEmbeddingService
    
    service = HuggingFaceEmbeddingService(settings)
    vectors = await service.embed_documents(["text1", "text2"])
"""

from app.embedding.huggingface import HuggingFaceEmbeddingService

__all__ = ["HuggingFaceEmbeddingService"]
