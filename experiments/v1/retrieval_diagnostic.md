# Retrieval Diagnostic Report

## Objective
Determine why the Phase 12 experiment retrieved exactly 0 chunks across all architectures.

## Diagnostic Execution
A direct diagnostic was executed against the production ChromaDB instance (`./chroma_db`) using the `HuggingFaceEmbeddingService`.

- **Collection Used**: `infra_documents`
- **Total Vectors**: 268
- **Similarity Scores Returned**: 0.77 – 0.86

## Root Cause Analysis
The vector store genuinely contains the documents (268 chunks). The `HuggingFaceEmbeddingService` correctly encodes the queries and successfully finds semantic matches with high cosine similarity (score > 0.77). 

However, `app/vectorstore/retriever.py` imposes the following hardcoded filter during retrieval when no workspace is specified:
```python
where_filter = {"is_global": True}
```
An inspection of the chunk metadata in ChromaDB reveals:
```json
{
  "document_id": "6a7990b8c902988cd052c9d3", 
  "page_number": 1, 
  "chunk_index": 0, 
  "document_name": "DRCS Cover - To author.pdf",
  "start_char": 0,
  "end_char": 995
}
```
The `is_global` metadata field was **never stored** during the ingestion phase. Because ChromaDB applies an exact metadata match, `{"is_global": True}` immediately filters out 100% of the database.

## Secondary Finding (Dataset Split)
The benchmark contains Q3: *"BUILDING INSPECTION REPORT Building: Government Office Complex"*. The source document for this query (`test_building_report.pdf`) was discovered in a separate collection named `building_documents` (which has exactly 2 chunks). It is not present in `infra_documents`. The experiment script only queries `infra_documents` via the application's config `CHROMADB_COLLECTION=infra_documents`. 

## Conclusion
**Classification**: RETRIEVAL_FILTER_ERROR

The retrieval returned zero chunks because the application's default retrieval filter (`is_global=True`) inadvertently blacklists the entire knowledge base due to a missing metadata flag from the ingestion phase. 

*(Note: We are not modifying the application architecture to fix this for the corrected pilot. We will address this strictly in the experiment runner script by passing an explicit `workspace_id` or overriding the retrieval call if necessary, or simply acknowledging it if we must reconstruct the test harness without altering `retriever.py`).*
