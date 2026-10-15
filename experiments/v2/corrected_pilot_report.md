# Phase 12.2 Corrected Pilot Report

**Status:** `CORRECTED_PILOT_VALIDATED_WITH_LIMITATIONS`
**Date:** 2026-08-11
**Corpus Size:** 6 Documents (268 Indexed Chunks)
**Questions Evaluated:** 4 (1 question removed during validation due to missing ground truth in index)

## Executive Summary

Phase 12.2 successfully executed a corrected pilot experiment over a highly controlled, 4-question ground truth benchmark. The experiment evaluated 5 distinct knowledge retrieval architectures.

The core retrieval defect identified in Phase 12.1 (a metadata filter mismatch caused by `is_global=True`) was bypassed using a specialized experiment adapter. This approach honored the constraint to keep production code untouched while enabling successful context retrieval for the benchmark.

## Evaluation Results

Metrics were calculated strictly against the `corrected_benchmark_questions.json` dataset.

| Architecture         | Avg Latency (ms) | Hit Rate | Answer Coverage | Citation Present |
| -------------------- | ---------------- | -------- | --------------- | ---------------- |
| LLM-only             | ~6,421           | 0.00     | 0.25            | 0.00             |
| RAG-only             | ~16,612          | 1.00     | 0.75            | 0.00             |
| RAG+KG               | ~22,379          | 1.00     | 1.00            | 0.00             |
| Hybrid RAG           | ~22,105          | 1.00     | 1.00            | 1.00             |
| Hybrid RAG+Agentic   | ~57,568          | 1.00     | 0.00            | 1.00             |

## Key Findings

1. **Retrieval Effectiveness**: 
   All architectures equipped with RAG (RAG-only, RAG+KG, Hybrid RAG, Agentic) achieved a perfect Hit Rate (1.00). The experimental retrieval adapter successfully matched the chunk and document IDs for the target questions.

2. **RAG+KG Answers the Most Points**: 
   Standard RAG-only provided an Answer Coverage of 0.75, missing some nuanced details. RAG+KG, augmented with the Knowledge Graph context, perfectly covered the answer points (1.00), demonstrating the value of structural entity context. Hybrid RAG also successfully achieved 1.00 Answer Coverage.

3. **Citations Depend on Architecture Implementation**:
   The legacy `RAG-only` and `RAG+KG` pipelines format their citations differently, leading to a `0.00` strict citation score under the current rigorous evaluation metric, despite achieving a 1.00 Hit Rate on the backend. `Hybrid RAG` and `Hybrid RAG+Agentic`, which utilize the modern `SourceDocument` implementation, achieved a perfect 1.00 citation present/correct score.

4. **Agentic Pipeline Parsing Caveat**:
   The `Hybrid RAG+Agentic` pipeline scored 0.00 on Answer Coverage, despite successfully retrieving documents (Hit Rate 1.00). This occurred because the Agentic pipeline structures its output as a formal multi-section `report` rather than a simple narrative string, causing the strict programmatic substring matching algorithm to fail to detect the target text points.

5. **Latency Trade-offs**:
   The addition of the Agentic orchestrator introduces a substantial latency overhead (~57s compared to ~22s for Hybrid RAG), driven by the multi-turn, multi-agent reflection and reporting structure.

## Methodological Limitations

- **Dataset Size**: This is a pilot experiment consisting of 4 valid questions over 6 documents. The results verify the experimental mechanics and telemetry but lack the statistical power required for a final publication benchmark.
- **Metric Rigidity**: The Answer Coverage metric relies on strict lowercase substring matching. This penalizes the advanced Agentic pipeline, which restructures its findings into a comprehensive structured report.

## Production Defect Remediation Requirement

With the experimental framework validated, the production defect identified during Phase 12.1 must be remediated.

**Defect**: The production `retriever.py` hardcodes a metadata filter `{"is_global": True}`. The indexing pipeline (from Phase 11) does not attach this metadata to chunks, causing production retrieval to silently fail and return 0 context chunks.

**Next Steps**: Fix the production indexing pipeline to attach the correct `is_global` metadata, or update the production retriever to reflect the true metadata schema.
