import pytest
from app.utils.text_splitter import TextChunk
from app.vectorstore.indexer import ChromaIndexer
from app.vectorstore.connection import get_building_collection, init_vectorstore
from app.embedding.huggingface import HuggingFaceEmbeddingService
import uuid
import asyncio

class MockEmbeddingService:
    async def embed_documents(self, texts):
        # Return dummy embeddings of size 384 (all-MiniLM-L6-v2)
        return [[0.1] * 384 for _ in texts]

@pytest.mark.asyncio
async def test_ingestion_metadata_preservation():
    from app.config import get_settings
    import app.vectorstore.connection as conn
    await conn.init_vectorstore(get_settings())
    # Setup indexer with mock embedding
    indexer = ChromaIndexer(embedding_service=MockEmbeddingService())
    
    # 1. Global Document Chunk
    global_chunk = TextChunk(
        document_id="global_doc_1",
        document_name="global.pdf",
        chunk_index=0,
        text="Global building text",
        start_char=0,
        end_char=20,
        metadata={"is_global": True}
    )
    
    # 2. Workspace Document Chunk
    workspace_id = str(uuid.uuid4())
    workspace_chunk = TextChunk(
        document_id="workspace_doc_1",
        document_name="workspace.pdf",
        chunk_index=0,
        text="Workspace building text",
        start_char=0,
        end_char=23,
        metadata={"is_global": False, "workspace_id": workspace_id, "category": "INSPECTION"}
    )
    
    # Index both
    await indexer.index_chunks([global_chunk, workspace_chunk])
    
    # Verify in ChromaDB
    collection = get_building_collection()
    
    # Check Global Doc
    global_results = collection.get(where={"document_id": "global_doc_1"}, include=["metadatas"])
    assert len(global_results["metadatas"]) == 1
    g_meta = global_results["metadatas"][0]
    assert g_meta["is_global"] == True
    assert "workspace_id" not in g_meta or g_meta["workspace_id"] is None
    
    # Check Workspace Doc
    workspace_results = collection.get(where={"document_id": "workspace_doc_1"}, include=["metadatas"])
    assert len(workspace_results["metadatas"]) == 1
    w_meta = workspace_results["metadatas"][0]
    assert w_meta["is_global"] == False
    assert w_meta["workspace_id"] == workspace_id
    assert w_meta["category"] == "INSPECTION"

    # Cleanup
    await indexer.delete_document_chunks("global_doc_1")
    await indexer.delete_document_chunks("workspace_doc_1")
