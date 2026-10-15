# Final Research Experiment Result Tables

## Table 1: System-wide Reliability and Latency Metrics

| Architecture | Runs | Success (%) | Failure (%) | Rate Limited (%) | Early Rejects | Mean Latency (ms) | Median Latency (ms) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **A. LLM-Only** | 8 | 75.00% | 0.00% | 2.00 | 0 | 18570.68 | 4505.62 |
| **B. RAG-Only** | 8 | 62.50% | 0.00% | 3.00 | 0 | 28140.53 | 26682.10 |
| **C. RAG + KG** | 8 | 62.50% | 0.00% | 3.00 | 0 | 22555.23 | 19950.42 |
| **D. Hybrid RAG** | 8 | 62.50% | 0.00% | 3.00 | 0 | 17712.73 | 17893.44 |
| **E. Hybrid Agentic** | 7 | 57.14% | 0.00% | 3.00 | 0 | 46774.44 | 46232.74 |

## Table 2: Retrieval & Grounding Precision Metrics

| Architecture | Hit Rate@1 | Hit Rate@5 | MRR | Citation Rate (%) | Doc Correctness (%) | Page Correctness (%) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **A. LLM-Only** | N/A | N/A | N/A | 0.0% | N/A | N/A |
| **B. RAG-Only** | 1.00 | 1.00 | 1.00 | 100.00% | 100.00% | 0.00% |
| **C. RAG + KG** | 1.00 | 1.00 | 1.00 | 100.00% | 100.00% | 0.00% |
| **D. Hybrid RAG** | 1.00 | 1.00 | 1.00 | 100.00% | 100.00% | 0.00% |
| **E. Hybrid Agentic** | 0.71 | 0.71 | 0.71 | 71.43% | 100.00% | 0.00% |