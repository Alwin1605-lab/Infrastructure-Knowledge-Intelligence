# Experiment Fairness Audit

## Objective
Verify that the Phase 12 Pilot Experiment provided a balanced and fair evaluation environment across all five architectures, ensuring that the isolated variable was strictly the pipeline architecture.

## Fairness Checklist

- **Same questions**: YES
  All five architectures were evaluated against the exact same 5 queries extracted from `benchmark_questions.json` in the same sequential run.
- **Same corpus**: YES
  All architectures accessed the exact same underlying ChromaDB (`infra_documents`) and Neo4j collections. (Note: As identified in the Ground Truth Audit, the corpus lacked the necessary chunks, but it lacked them equally for all architectures).
- **Same benchmark**: YES
  The same ground truth targets were used for the automated evaluation script (`12_03_calculate_metrics.py`).
- **Same model**: YES
  All architectures used `llama-3.1-8b-instant` via the Groq provider for LLM generation, and `all-MiniLM-L6-v2` for embeddings.
- **Same runtime environment**: YES
  All pipelines were instantiated sequentially within the same `12_02_run_experiment.py` process, running against the same local Docker infrastructure. Timeouts and rate limits were enforced equally (via `asyncio.sleep(2)` between queries).
- **Same evaluation methodology**: YES
  The `12_03_calculate_metrics.py` script applied the identical evaluation loops to the outputs of every architecture.
- **Architecture-specific differences documented**: YES
  The Latency Audit explicitly documents that Hybrid RAG executed an Early Rejection path, terminating in ~26ms without calling the LLM, whereas other architectures underwent full execution.

## Conclusion
The experimental test harness is fundamentally fair and executes controlled ablation. The isolated variable in the experiment was strictly the architectural pipeline. The issues discovered in this audit phase (e.g., Hit Rate 0.0, Citation Coverage 1.0) stem from the *evaluator script* and *benchmark ground truth*, not from an unfair execution environment.
