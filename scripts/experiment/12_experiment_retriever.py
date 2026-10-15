"""Experiment-Only Retrieval Adapter

This adapter exists strictly to isolate a known ingestion-metadata defect during the Phase 12.2 controlled research evaluation.
It does NOT modify production application behavior.

Production `retriever.py` filters by `{"is_global": True}`, but Phase 10/11 ingestion omitted this field,
causing 0 chunks to be retrieved. This adapter omits the filter to accurately evaluate the actual indexed vector capability.
"""

from typing import Optional, List
import chromadb
from app.config import get_settings
from app.vectorstore.retriever import RetrievedChunk
from app.embedding.huggingface import HuggingFaceEmbeddingService

class ExperimentRetriever:
    def __init__(self, embedding_service: HuggingFaceEmbeddingService, similarity_threshold: float = 0.0):
        self._embedding_service = embedding_service
        self._similarity_threshold = similarity_threshold
        # Connect to Chroma explicitly using the expected path
        self._client = chromadb.PersistentClient(path="./chroma_db")
        settings = get_settings()
        self._collection = self._client.get_collection(settings.CHROMADB_COLLECTION)
        
    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        workspace_id: Optional[str] = None
    ) -> List[RetrievedChunk]:
        
        if not query or not query.strip():
            return []
            
        # Embed using exact same model
        query_embedding = await self._embedding_service.embed_text(query)
        
        # Query ChromaDB directly WITHOUT the "is_global: True" filter
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, self._collection.count() or 1),
            include=["documents", "metadatas", "distances"]
        )
        
        retrieved: List[RetrievedChunk] = []
        if not results["ids"] or not results["ids"][0]:
            return []
            
        for doc_id, text, metadata, distance in zip(
            results["ids"][0],
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        ):
            # Chroma returns cosine distance (0 to 2)
            relevance_score = max(0.0, 1.0 - (distance / 2.0))
            
            if relevance_score < self._similarity_threshold:
                continue
                
            chunk = RetrievedChunk(
                text=text,
                document_id=metadata.get("document_id", ""),
                document_name=metadata.get("document_name", "unknown"),
                relevance_score=round(relevance_score, 4),
                page_number=metadata.get("page_number"),
                section=metadata.get("section"),
                chunk_index=metadata.get("chunk_index", 0)
            )
            retrieved.append(chunk)
            
        retrieved.sort(key=lambda c: c.relevance_score, reverse=True)
        return retrieved

    async def retrieve_for_context(
        self,
        query: str,
        top_k: int = 5,
        workspace_id: Optional[str] = None
    ) -> str:
        chunks = await self.retrieve(query, top_k=top_k, workspace_id=workspace_id)
        if not chunks:
            return "No relevant building engineering documents found in the knowledge base."
            
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            citation = chunk.to_citation_string()
            context_parts.append(
                f"**[Source {i}]** {citation} (relevance: {chunk.relevance_score:.2f})\n\n"
                f"{chunk.text}"
            )
        return "\n\n---\n\n".join(context_parts)
