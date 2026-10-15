# Revised Pilot Interpretation

## 1. Experimental Execution
**OBSERVED FACTS:**
- The experimental script (`12_02_run_experiment.py`) executed 25 runs (5 questions × 5 architectures) without crashing.
- Rate limits and timeouts were successfully managed via delays.
- Hybrid RAG bypassed LLM generation via its confidence/grounding strictness, returning early in ~26ms.
- All other architectures executed full LLM generation loops.

**INTERPRETATION:**
The execution framework (pipeline instantiation, query routing, async coordination, and fault tolerance) is structurally sound and ready for research use.

**LIMITATIONS:**
The 25-run size is insufficient for statistically significant conclusions, regardless of metric validity.

## 2. Metric Validity
**OBSERVED FACTS:**
- Vector retrieval returned 0 chunks across all queries for all architectures.
- The evaluation script awarded a 1.00 Point Coverage score to the Hybrid RAG fallback message.
- The evaluation script awarded a 1.00 Citation Coverage score across all runs because it searched for an empty string.
- The ground truth chunks and proper source mappings are absent from the benchmark JSON.

**INTERPRETATION:**
The automated evaluation script (`12_03_calculate_metrics.py`) contains logical flaws that artificially inflate coverage scores. It cannot distinguish between a successful answer and an exact-match fallback message, nor can it handle missing ground-truth citations safely.

**LIMITATIONS:**
Because the underlying automated metrics evaluate to INVALID or NOT_VERIFIABLE, no comparative conclusions can be drawn about which architecture performs better at retrieval or generation.

## Final Research Status

**PILOT_REQUIRES_CORRECTION**

The pipeline itself works flawlessly, but the *benchmark dataset* and *evaluation script* must be corrected before a formal research experiment can be conducted.
