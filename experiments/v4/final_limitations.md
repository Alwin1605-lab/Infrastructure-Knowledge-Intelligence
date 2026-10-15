# Final Experiment Limitations Report

## 1. Cloud Provider Quota & Daily Rate Limits
- Groq cloud API enforces a strict daily limit of **250 Requests Per Day (RPD)** on free-tier access (`groq/compound-mini`). This rate limit halted execution at 39 live requests, marking the remaining 486 runs as `RATE_LIMITED`.

## 2. Hardware & Local Inference Constraints
- Embedding generation (`all-MiniLM-L6-v2`) and local vector retrieval ran in CPU host mode.