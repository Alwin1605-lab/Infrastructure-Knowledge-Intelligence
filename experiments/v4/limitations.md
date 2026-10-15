# Research Experiment Limitations

## 1. External API Quota & Rate Limits
- The experiment uses the Groq cloud LLM provider (`groq/compound-mini`). Free-tier rate limits (30 RPM, 100k TPD) require exponential backoff and retry handling.

## 2. Corpus Domain Boundary
- The frozen research corpus consists of 20 verified building engineering documents (355 pages). While highly diverse across 5 sub-domains, findings may differ for non-building civil engineering domains (e.g. aerospace or highway engineering).

## 3. Hardware Execution Environment
- Local vector retrieval and embedding generation (`all-MiniLM-L6-v2`) ran on CPU host environment. System latency reflects single-threaded CPU embedding calculation.