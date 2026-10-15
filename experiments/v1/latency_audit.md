# Latency Methodology Audit

## Objective
Verify that all architectures measure latency using the same definition, and classify whether the latencies are directly comparable across the five architectures tested in the Phase 12 Pilot.

## Measurement Methodology
In `12_02_run_experiment.py`, latency is measured using the following block:
```python
start_time = time.time()
try:
    if arch == "LLM-only":
        ...
    elif arch == "Hybrid RAG":
        ...
except Exception as e:
    ...
run_result["latency_ms"] = int((time.time() - start_time) * 1000)
```
This correctly ensures that:
- `START` is immediately before architecture execution.
- `END` is immediately after final response generation (or failure).
- Dataset loading, vectorstore initialization, and JSON writing are executed outside this timer.

## Architecture Breakdown

| Architecture | Mean (ms) | Median (ms) | Min (ms) | Max (ms) | Execution Type | Comparable? |
|--------------|-----------|-------------|----------|----------|----------------|-------------|
| **LLM-only** | 10,290 | 925 | 737 | 40,882 | Single LLM API Call | YES |
| **RAG-only** | 15,816 | 8,758 | 451 | 53,198 | Chroma Query + LLM Call | YES |
| **RAG+KG** | 9,567 | 4,838 | 560 | 34,449 | Chroma + Neo4j + LLM Call | YES |
| **Hybrid RAG** | 26 | 27 | 19 | 36 | Early Rejection (No LLM Call) | **NO** |
| **Hybrid RAG+Agentic**| 20,326 | 23,419 | 2,799 | 28,476 | Agent Orchestration Loop | YES |

*(Note: With only five samples per architecture, P95 values are not statistically meaningful and are omitted).*

## Hybrid RAG Latency Discrepancy
The **Hybrid RAG** architecture returned a mean latency of ~26 ms.
An audit of the execution traces reveals that Hybrid RAG enforces a strict grounding threshold. Because 0 chunks and 0 entities were retrieved for the pilot queries, Hybrid RAG's `ContextFuser` and `ConfidenceScorer` immediately scored the context as `confidence=0.0`. 
Consequently, the pipeline triggered an **EARLY_REJECTION** and returned a static fallback string (*"I don't have sufficient information..."*) without ever calling the LLM generation endpoint.

Because it bypassed the 5,000–30,000 ms network call required by all other architectures, its latency is **NOT COMPARABLE** to the other pipelines that performed full generation.

## Conclusion
The latency timing methodology itself is fundamentally sound. However, the resulting measurements cannot be blindly compared in an ablation table because Hybrid RAG executed a fundamentally different path (Partial Execution / Early Rejection) compared to the others.
