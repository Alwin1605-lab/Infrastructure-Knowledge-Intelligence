# Ground Truth & Hit Rate Audit

## Objective
Determine whether the Hit Rate@5 metric reported in Phase 12 (0.00 for all architectures) reflects a true retrieval failure (ZERO) or an evaluation failure (NOT_VERIFIABLE).

## Benchmark Ground Truth Inspection

An inspection of `benchmark_questions.json` reveals the following structure for each question:
```json
{
  "ground_truth_documents": ["6a7990b8c902988cd052c9d3"],
  "ground_truth_evidence": ["HIGHER EDUCATION \\nREINFORCED\\n...stude..."],
  "ground_truth_entities": [],
  "expected_answer_points": ["HIGHER EDUCATION REINFORCED CONCRETE STRUCTURES N SUBRAMANIAN..."]
}
```

### Analysis of Fields
1. **`ground_truth_documents`**: Contains valid MongoDB ObjectIDs. However, these are document-level, not chunk-level.
2. **`ground_truth_chunks`**: This field is completely MISSING from the benchmark dataset. There is no mapping to the actual chunk IDs stored in ChromaDB.
3. **`ground_truth_evidence`**: Contains text strings, but they are truncated (e.g., ending in `stude...`).

## Evaluation Methodology (Hit Rate@5)
The script `12_03_calculate_metrics.py` calculates a hit if:
`gt_text in retrieved_chunk_text` OR `retrieved_chunk_text in gt_text`.

Because `gt_text` is synthetically truncated with `...`, it will *never* be a pure substring of the actual ChromaDB chunk text. Likewise, the full ChromaDB chunk text will never be a substring of the truncated `gt_text`.

Furthermore, since `ground_truth_chunks` is entirely absent, we cannot do a direct ID-based intersection check.

## Conclusion

The `Hit Rate@5` metric is **NOT_VERIFIABLE**.
The value `0.00` reported in the Phase 12 pilot is mathematically invalid because the ground truth evidence provided in the benchmark dataset is synthetically truncated and incompatible with substring-based validation. The absence of explicit chunk ID mappings prevents deterministic validation.

**Final Classification**: NOT_VERIFIABLE
