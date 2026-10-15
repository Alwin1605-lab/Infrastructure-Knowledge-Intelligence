# Complete Research Experiment Result Tables

## Table 1: Complete 525-Run Terminal Status Matrix

| Architecture | Expected Runs | SUCCESS Runs | Rate Limited Runs | Failed Runs | Mean Latency (ms) | Median Latency (ms) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **A. LLM-Only** | 105 | 6 | 99 | 0 | 3971.21 | 3581.23 |
| **B. RAG-Only** | 105 | 5 | 100 | 0 | 21322.09 | 25139.05 |
| **C. RAG + KG** | 105 | 5 | 100 | 0 | 13336.39 | 14910.08 |
| **D. Hybrid RAG** | 105 | 5 | 100 | 0 | 11488.09 | 9111.75 |
| **E. Hybrid Agentic** | 105 | 4 | 101 | 0 | 51103.14 | 51407.35 |

## Table 2: Benchmark Domain Distribution (105 Questions)

| Domain | Question Count | Percentage |
| :--- | :---: | :---: |
| Building Guidelines, Codes & Facility Specifications | 23 | 21.9% |
| Concrete Durability & Carbonation | 17 | 16.2% |
| Geotechnical & Foundation Engineering | 18 | 17.1% |
| Inspection & Structural Health Monitoring | 26 | 24.8% |
| Seismic & Structural Retrofitting | 21 | 20.0% |