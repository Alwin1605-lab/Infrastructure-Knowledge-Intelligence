# Phase 12.1 Results Audit

## Overview
This document audits the raw experimental output generated during Phase 12 to verify that the reported metrics reflect true system performance.

## 1. LLM-only Architecture
- **Execution Status**: SUCCESS for all 5 queries.
- **Latency**: Fully executed (mean ~10,290 ms).
- **Retrieval Results**: Not applicable (0 chunks retrieved).
- **Generated Answer**: LLM returned hallucinated or generalized answers without context.
- **Answer Point Coverage**: Erroneously calculated due to evaluator bug (see below).
- **Citation Coverage**: Erroneously calculated as 1.00 for all queries due to missing `source_document` field in the benchmark ground truth mapping.

## 2. RAG-only Architecture
- **Execution Status**: SUCCESS for all 5 queries.
- **Latency**: Fully executed (mean ~15,816 ms).
- **Retrieval Results**: Vector search returned 0 relevant chunks for all queries (Hit Rate = 0).
- **Generated Answer**: LLM generated answers based on the prompt, but without grounding context, it largely hallucinated or returned generic statements.

## 3. RAG+KG Architecture
- **Execution Status**: SUCCESS for all 5 queries.
- **Latency**: Fully executed (mean ~9,567 ms).
- **Retrieval Results**: Vector search returned 0 chunks. Knowledge Graph returned 0 entities.
- **Generated Answer**: Similar to RAG-only, the LLM had to guess.

## 4. Hybrid RAG Architecture
- **Execution Status**: EARLY_REJECTION.
- **Latency**: ~26 ms.
- **Retrieval Results**: 0 chunks.
- **Generated Answer**: The system returned a programmatic fallback message: *"I don't have sufficient information in the provided building engineering documents to answer the question: [Question Text]"*
- **Audit Finding**: The evaluator incorrectly awarded 1.00 Point Coverage because the fallback message echoes the question text, and the benchmark's `expected_answer_points` are exact substrings of the question text. This is an EVALUATOR ERROR.

## 5. Hybrid RAG+Agentic Architecture
- **Execution Status**: FULL_EXECUTION (mean ~20,326 ms).
- **Retrieval Results**: 0 chunks, 0 entities.
- **Generated Answer**: The agents successfully executed 4-5 reasoning steps. Because context was missing, the Report Agent produced a critical condition report, often hallucinating a detailed structural audit response or providing a generalized maintenance response.
- **Agent Trace**: Present and valid.

## Conclusion
The experimental pipeline executed correctly, but the underlying evaluation metrics are flawed. Specifically:
1. `Citation Coverage` evaluates to 1.00 because it searches for an empty string.
2. `Point Coverage` evaluates to 1.00 for Hybrid RAG because the fallback message echoes the question text.
3. `Hit Rate@5` is 0.00 because the vector search genuinely failed to find the documents.
