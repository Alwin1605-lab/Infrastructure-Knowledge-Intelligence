# API Reference

The Building Knowledge Intelligence System exposes a FastAPI backend natively available on port `8000`. You can test these interactively using the built-in Swagger UI at `http://localhost:8000/docs`.

## 1. System Health & Observability

### `GET /api/v1/health/system`
Retrieves comprehensive system health, dependencies status, and component versioning.

**Response**
```json
{
  "status": "ok",
  "versions": {
    "backend_version": "0.9.0",
    "api_version": "v1",
    "pipeline_version": "Agentic-v2",
    "frontend_version": "0.8.0",
    "kb_version": "v1.0"
  },
  "services": {
    "mongodb": "ok",
    "neo4j": "ok",
    "chromadb": "ok",
    "groq_llm": "ok"
  },
  "knowledge_base": {
    "documents_indexed": 59,
    "kg_nodes": 12438,
    "kg_relationships": 34782
  }
}
```

## 2. Agentic AI Pipeline (Phase 6)

### `POST /api/v1/agents/query`
Sends an engineering question to the 5-Agent orchestration pipeline. This handles intent parsing, Hybrid RAG, Knowledge Graph Reasoning, Recommendation Generation, and Final Report Synthesis.

**Request Body**
```json
{
  "question": "What is the standard repair method for spalling in reinforced concrete beams?",
  "top_k": 5
}
```

**Response**
```json
{
  "overall_confidence": 0.94,
  "report": "Spalling in reinforced concrete beams is typically repaired by...",
  "rag_response": {
    "answer": "...",
    "sources": [
      {
        "document_name": "IS_456_2000.pdf",
        "page": 24,
        "chunk_preview": "Spalling repairs require...",
        "relevance_score": 0.88
      }
    ],
    "recommendations": [
      {
        "action": "Remove loose concrete back to sound material",
        "priority": "high",
        "reason": "Prevents further propagation of the defect.",
        "standards_reference": "IS 456"
      }
    ]
  },
  "execution_trace": [
    {
      "agent": "QueryAnalysisAgent",
      "status": "success",
      "time_ms": 45,
      "reason": "Classified intent as REPAIR. Extracted entities: 'spalling', 'reinforced concrete beam'.",
      "confidence": 0.98
    },
    {
      "agent": "RetrievalAgent",
      "status": "success",
      "time_ms": 120,
      "reason": "Retrieved 5 chunks from ChromaDB.",
      "confidence": 0.92
    }
  ]
}
```

## 3. Evaluation & Benchmarking (Phase 7)

### `POST /api/v1/eval/benchmark`
Executes an automated benchmark against a predefined dataset. Calculates retrieval coverage, MRR, Hit Rate, and generates failure classifications.

### `GET /api/v1/eval/history`
Retrieves a JSON list of all previously executed benchmarks, displaying historical accuracy and latency improvements over time.

### `POST /api/v1/eval/ablation`
Runs a specific query through 5 different architectural configurations (LLM-Only -> Hybrid RAG -> Agentic AI) simultaneously for comparative explainability.
