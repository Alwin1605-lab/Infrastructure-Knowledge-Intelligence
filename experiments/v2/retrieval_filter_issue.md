# Production Retrieval Defect Documentation

## Overview
This document explains the discrepancy between the production application's retrieval logic and the isolated retrieval adapter used in the corrected Phase 12.2 pilot experiment.

## Production Behavior
The application's core retriever (`app/vectorstore/retriever.py`) enforces the following filter when no explicit workspace ID is requested:
```python
where_filter = {"is_global": True}
```
During the actual ingestion phase (Phase 10/11), the document metadata appended to ChromaDB chunks **did not include** the `is_global` boolean field. Consequently, the production vector search evaluates against an empty dataset, yielding zero results for all queries regardless of semantic similarity.

## Experimental Behavior
The controlled Phase 12.2 experiment evaluates the underlying architectures using an **Experiment-Only Retrieval Adapter**. 

The adapter strictly maintains:
- The identical ChromaDB instance (`infra_documents` collection).
- The identical HuggingFace embedding model (`all-MiniLM-L6-v2`) and dimensionality.
- The identical preprocessed query text.
- The same corpus data.

The adapter explicitly **omits** the incorrect `is_global` filter, allowing the vector search to return the actual stored chunks based on the configured similarity threshold.

## Limitation and Disclaimer
**This adapter exists only to isolate the known ingestion-metadata defect during controlled research evaluation. It does not modify production application behavior.**

The production retrieval path contains a metadata-filter mismatch because indexed documents lack the expected `is_global` metadata field. The controlled experiment therefore uses an isolated retrieval adapter without this filter to evaluate the underlying indexed retrieval capability. The production defect remains separately identified for remediation.
