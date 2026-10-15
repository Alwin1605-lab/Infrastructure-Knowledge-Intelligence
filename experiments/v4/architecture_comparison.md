# Five-Architecture Side-by-Side Comparison

**Generated:** 2026-08-19T08:54:22.898009+00:00Z

## Architectural Matrix

| Feature / Parameter | Arch A (LLM-Only) | Arch B (RAG-Only) | Arch C (RAG + KG) | Arch D (Hybrid RAG) | Arch E (Hybrid Agentic) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Vector Retrieval** | No | Yes (ChromaDB) | Yes (ChromaDB) | Yes (ChromaDB) | Yes (ChromaDB) |
| **Knowledge Graph** | No | No | Yes (Neo4j) | Yes (Neo4j) | Yes (Neo4j) |
| **Reranking / Confidence** | No | No | No | Yes (Confidence Filter) | Yes |
| **Early Rejection** | No | No | No | Yes (< 0.25 threshold) | No |
| **Multi-Step Agent Reasoning** | No | No | No | No | Yes (3 Steps) |

## Measured Performance Overview

| Architecture | Success Rate | Mean Latency (ms) | P95 Latency (ms) | Citation Rate | Doc Correctness |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **A. LLM-Only** | 75.00% | 18570.68 | 72853.55 | 0.0% | N/A |
| **B. RAG-Only** | 62.50% | 28140.53 | 50527.28 | 100.00% | 100.00% |
| **C. RAG + KG** | 62.50% | 22555.23 | 46919.77 | 100.00% | 100.00% |
| **D. Hybrid RAG** | 62.50% | 17712.73 | 28999.02 | 100.00% | 100.00% |
| **E. Hybrid Agentic** | 57.14% | 46774.44 | 65400.22 | 71.43% | 100.00% |