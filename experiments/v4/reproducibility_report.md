# Research Reproducibility Report

## 1. Frozen Baseline SHA256 Hashes
- **Corpus Inventory SHA256:** `75a68942838d1d5c3fee1ae1726abf594307743f8873ace19dd1ab030548033f`
- **Benchmark Questions SHA256:** `803b61b1c1ebde180af200bc1e830486dfbe9ddce2b48d41b3526fd37fd939b3`
- **Raw Results SHA256:** `4f95bf8074c8b3094fbdb5de5464bd81490d4dee20c463352b6178261c3eaa0f`

## 2. System & Model Specifications
- **Embedding Model:** `all-MiniLM-L6-v2` (384-dim, cosine distance)
- **LLM Provider & Model:** `groq/compound-mini`
- **Chunk Size / Overlap:** 1000 / 200
- **ChromaDB Collection:** `building_documents` (1,066 vectors)
- **Neo4j Graph DB:** `infra_knowledge` (401 entities, 1108 relationships)

## 3. Steps to Reproduce
1. Start database containers: `docker compose up -d mongodb neo4j chromadb`
2. Verify corpus discovery: `python scripts/13_01_discover_corpus.py`
3. Run experiment suite: `python scripts/14_01_run_final_experiment.py`
4. Calculate metrics: `python scripts/14_02_calculate_final_metrics.py`
5. Generate research reports: `python scripts/14_03_generate_research_reports.py`