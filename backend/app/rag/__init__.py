"""Hybrid RAG Pipeline — Phase 5.

Combines semantic vector retrieval (ChromaDB) with structured graph traversal (Neo4j)
to produce grounded, citation-backed answers for building engineering queries.

Pipeline stages:
    1. QueryProcessor  — domain guard + entity extraction + query expansion
    2. ChromaRetriever — semantic similarity search (existing)
    3. KG Traversal    — defect/component subgraph retrieval (existing queries.py)
    4. ChunkReranker   — keyword-boosted re-scoring
    5. ContextFuser    — unified RAG context construction
    6. GroqLLM         — answer generation (existing BaseLLMProvider)
    7. ConfidenceScorer — grounding assessment
    8. ResponseParser  — typed ChatResponse assembly

Domain: Buildings Only (RCC, Residential, Commercial, Institutional, Government).
"""

from app.rag.pipeline import HybridRAGPipeline
from app.rag.query_processor import QueryProcessor, ProcessedQuery
from app.rag.reranker import ChunkReranker
from app.rag.context_fusion import ContextFuser, FusedContext
from app.rag.confidence import ConfidenceScorer
from app.rag.response_parser import ResponseParser

__all__ = [
    "HybridRAGPipeline",
    "QueryProcessor",
    "ProcessedQuery",
    "ChunkReranker",
    "ContextFuser",
    "FusedContext",
    "ConfidenceScorer",
    "ResponseParser",
]
