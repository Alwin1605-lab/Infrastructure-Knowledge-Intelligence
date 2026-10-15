# Phase 12.2 - Corrected Pilot Experiment

This directory contains the artifacts for the Phase 12.2 Corrected Pilot Experiment. The goal of this phase was to resolve a retrieval failure identified in Phase 12.1 and execute a strictly controlled pilot over a 4-question ground-truth validated benchmark.

## Artifacts

1. `retrieval_filter_issue.md`: A root-cause analysis documenting a mismatch between the production metadata filter (`is_global=True`) and the actual indexed chunk metadata, explaining why retrieval returned 0 chunks in Phase 12.1.
2. `experiment_contract.json`: The explicit guidelines and rules governing this pilot execution, including a strict "No Fabrication" policy.
3. `live_corpus_snapshot.json`: A snapshot of the 268 chunks actually present in the live ChromaDB instance to ensure the ground truth matches reality.
4. `corrected_benchmark_questions.json`: The rebuilt benchmark derived from real indexed chunks. 4 out of 5 questions successfully validated and were retained.
5. `retrieval_diagnostic.md`: A diagnostic report proving the experiment retrieval adapter successfully returns data from ChromaDB, whereas the production retriever fails.
6. `corrected_raw_results.json`: The complete, untempered LLM JSON responses for the 4 valid questions across all 5 architectures.
7. `corrected_metrics.json`: The strict, programmatic evaluation of the raw results calculating Hit Rate, Answer Coverage, and Citation Accuracy.
8. `corrected_pilot_report.md`: The final analytical report summarizing the findings and acknowledging the limitations of this pilot.

## Methodology

- The production application (`retriever.py`) was **NOT** modified.
- To bypass the retrieval bug, the experiment utilized a specialized adapter (`scripts/12_experiment_retriever.py`).
- Ground truth was rebuilt using actual DB snapshots rather than PDF text parsing, guaranteeing that only truly retrievable content was marked as expected ground truth.
- The experiment was run across 5 architectures: LLM-only, RAG-only, RAG+KG, Hybrid RAG, and Hybrid RAG+Agentic.
- Missing answer points and empty fields were treated strictly as failures (`NOT_VERIFIABLE`).
