import pytest
import uuid
from app.vectorstore.indexer import ChromaIndexer
from app.vectorstore.retriever import ChromaRetriever
from app.vectorstore.connection import init_vectorstore
from app.utils.text_splitter import TextChunk
from tests.integration.test_ingestion_metadata import MockEmbeddingService

class MockQueryEmbeddingService(MockEmbeddingService):
    async def embed_text(self, text):
        return [0.1] * 384

@pytest.mark.asyncio
async def test_tenant_isolation():
    from app.config import get_settings
    import app.vectorstore.connection as conn
    await conn.init_vectorstore(get_settings())
    indexer = ChromaIndexer(embedding_service=MockQueryEmbeddingService())
    retriever = ChromaRetriever(embedding_service=MockQueryEmbeddingService())
    
    workspace_a = str(uuid.uuid4())
    workspace_b = str(uuid.uuid4())
    
    # Create chunks
    global_chunk = TextChunk(
        document_id="global_1", document_name="global.pdf", chunk_index=0,
        text="Unique Global Secret", start_char=0, end_char=10, metadata={"is_global": True}
    )
    wsa_chunk = TextChunk(
        document_id="wsa_1", document_name="wsa.pdf", chunk_index=0,
        text="Unique Workspace A Secret", start_char=0, end_char=10, metadata={"is_global": False, "workspace_id": workspace_a}
    )
    wsb_chunk = TextChunk(
        document_id="wsb_1", document_name="wsb.pdf", chunk_index=0,
        text="Unique Workspace B Secret", start_char=0, end_char=10, metadata={"is_global": False, "workspace_id": workspace_b}
    )
    
    await indexer.index_chunks([global_chunk, wsa_chunk, wsb_chunk])
    
    try:
        # Test 1: Guest (No Workspace) -> Should retrieve Global, but not WSA/WSB
        results_guest = await retriever.retrieve("Secret", top_k=5, workspace_id=None)
        doc_ids_guest = [c.document_id for c in results_guest]
        assert "global_1" in doc_ids_guest
        assert "wsa_1" not in doc_ids_guest
        assert "wsb_1" not in doc_ids_guest

        # Test 2: Workspace A -> Should retrieve Global and WSA, but not WSB
        results_wsa = await retriever.retrieve("Secret", top_k=5, workspace_id=workspace_a)
        doc_ids_wsa = [c.document_id for c in results_wsa]
        assert "global_1" in doc_ids_wsa
        assert "wsa_1" in doc_ids_wsa
        assert "wsb_1" not in doc_ids_wsa

        # Test 3: Workspace B -> Should retrieve Global and WSB, but not WSA
        results_wsb = await retriever.retrieve("Secret", top_k=5, workspace_id=workspace_b)
        doc_ids_wsb = [c.document_id for c in results_wsb]
        assert "global_1" in doc_ids_wsb
        assert "wsa_1" not in doc_ids_wsb
        assert "wsb_1" in doc_ids_wsb

    finally:
        await indexer.delete_document_chunks("global_1")
        await indexer.delete_document_chunks("wsa_1")
        await indexer.delete_document_chunks("wsb_1")
