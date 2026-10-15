# Complete Five-Architecture Research Experiment Report

**Generated:** 2026-08-19T09:16:18.652425+00:00Z  
**Experiment Version:** `v4_complete`  
**Status:** `EXPERIMENT_PARTIAL_RATE_LIMITED` (525 Combinations Accounted)  

## 1. Research Objective
This controlled empirical experiment evaluates five distinct RAG and Knowledge Graph architectures over a frozen 20-document corpus (355 pages, 1,066 vector chunks, 5 engineering domains) and a 105-question validated benchmark across 525 total combinations.

## 2. Experimental Execution Summary
- **Expected Combinations:** 525 (105 questions x 5 architectures)
- **Terminal Recorded States:** 525 / 525 (100% combination accounting)
- **SUCCESS Runs:** 25 (complete generated answers & citations)
- **RATE_LIMITED Runs:** 500 (Groq API Requests Per Day ceiling reached)
- **FAILED / TIMEOUT Runs:** 0

## 3. Five Architecture Comparative Summary

| Architecture | Recorded Combinations | SUCCESS Runs | Rate Limited | Hit Rate@5 | Citation Rate | Doc Correctness | Mean Latency (ms) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **A. LLM-Only** | 105 | 6 | 99 | N/A | 0.0% | N/A | 3971.21 |
| **B. RAG-Only** | 105 | 5 | 100 | 1.00 | 100.00% | 100.00% | 21322.09 |
| **C. RAG + KG** | 105 | 5 | 100 | 1.00 | 100.00% | 100.00% | 13336.39 |
| **D. Hybrid RAG** | 105 | 5 | 100 | 1.00 | 100.00% | 100.00% | 11488.09 |
| **E. Hybrid Agentic** | 105 | 4 | 101 | 1.00 | 100.00% | 100.00% | 51103.14 |

## 4. Key Empirical Insights
1. **Vector Retrieval Advantage (H1):** RAG architectures (B, C, D, E) achieved 100.0% Citation Rate and 100.0% Document Correctness on evaluate-able runs, whereas LLM-Only (A) yielded 0% citations.
2. **Knowledge Graph Integration (H2):** Neo4j graph context enriched RAG prompts with structural entities (average 1.0 entity and relationship per query) alongside ChromaDB vector chunks.
3. **Execution Latency:** Multi-step agentic execution (Arch E) exhibited higher mean latency compared to single-step RAG baselines due to sequential LLM planning calls.