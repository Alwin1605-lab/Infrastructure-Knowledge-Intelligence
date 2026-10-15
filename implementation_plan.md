# Phase 12.3: Production Retrieval Metadata Remediation & Re-indexing

This plan addresses the root cause of the retrieval defect identified in Phase 12.1 and establishes a robust remediation and testing strategy.

## 1. Root Cause Analysis
During document ingestion (`DocumentService.process_document`), the `is_global` and `workspace_id` flags were attached to the `TextChunk` object's `metadata` dictionary. However, the `ChromaIndexer._chunk_metadata` method, which is responsible for serializing metadata into ChromaDB, entirely ignored the `chunk.metadata` field, only keeping standard fields like `document_id`, `chunk_index`, etc. This caused all chunks to be written without `is_global` or `workspace_id` metadata.

When the production `ChromaRetriever` subsequently queries ChromaDB, it explicitly filters by `{"is_global": True}` or `{"$or": [{"is_global": True}, {"workspace_id": workspace_id}]}`. Because no chunks contain this metadata, 0 results are returned.

## 2. Proposed Changes

### [MODIFY] `backend/app/vectorstore/indexer.py`
- Modify `_chunk_metadata(chunk: TextChunk)` to merge `chunk.metadata` into the final metadata dictionary sent to ChromaDB. This guarantees that `is_global` and `workspace_id` are persisted.

### [NEW] `scripts/12_03_metadata_audit.py`
- Connects directly to ChromaDB (`infra_documents` collection).
- Retrieves all chunks and calculates counts for: total vectors, vectors with/without `is_global`, `is_global=True/False`, and missing keys (`document_id`, `workspace_id`, etc.).
- Groups the results by `document_id`.
- Outputs `experiments/v2/production_metadata_audit.md`.

### [NEW] `scripts/12_04_repair_chroma_metadata.py`
- A script with a mandatory `--dry-run` argument.
- Connects to both MongoDB and ChromaDB.
- Iterates over all ChromaDB chunks missing `is_global`.
- Looks up the parent document in MongoDB to determine its scope (Global vs Workspace).
- Prepares the ChromaDB `update` operations to inject `is_global` and `workspace_id` safely.
- Executes the repair only when `--dry-run` is not provided.

### [NEW] Tests
- **`backend/tests/integration/test_tenant_isolation.py`**: A new integration test suite explicitly verifying that Workspace A cannot retrieve Workspace B's documents, but can retrieve Global documents.
- **`backend/tests/integration/test_ingestion_metadata.py`**: A test that uploads a small document and verifies that the `is_global` and `workspace_id` flags make it into ChromaDB.

## 3. Execution Plan

1. **Audit phase**: Write and run `scripts/12_03_metadata_audit.py` to get a snapshot of the current metadata corruption.
2. **Backup**: Export the current metadata of ChromaDB to a backup JSON file (`experiments/v2/chroma_metadata_backup_<timestamp>.json`).
3. **Repair script creation**: Write `scripts/12_04_repair_chroma_metadata.py` and run it with `--dry-run`.
4. **User Review Required**: I will stop and present the `--dry-run` output and audit results for your review before modifying the database.
5. **Mutation**: Run the repair script without `--dry-run`.
6. **Code Fix**: Patch `indexer.py` to fix future ingestions.
7. **Verification**: Run `scripts/12_05_production_retrieval_verification.py` to ensure the production retriever now matches the experiment adapter.
8. **Testing**: Write and run the regression tests. Generate the final fix report.

## 4. Open Questions

- Is there a specific format you prefer for the `chroma_metadata_backup.json` (e.g., list of `{id, metadata}` pairs)?
