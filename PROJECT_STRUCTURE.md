# Building Knowledge Intelligence System — Project Structure

This document describes the organized architecture and directory layout of the Building Knowledge Intelligence System.

```
Infrastructure-Knowledge-Intelligence/
├── .env.example                  # Environment variable configuration template
├── .gitignore                    # Git tracking ignore rules
├── .dockerignore                 # Docker build ignore context rules
├── docker-compose.yml            # Infrastructure container orchestrator (MongoDB, Neo4j, ChromaDB, Backend, Frontend)
├── README.md                     # System architecture & deployment guide
├── PROJECT_STRUCTURE.md          # Comprehensive codebase tree & folder reference
│
├── backend/                      # FastAPI Python Backend Application
│   ├── app/                      # Main Application Source Code
│   │   ├── agents/               # LangChain Agentic RAG Multi-Agent Pipeline
│   │   ├── api/                  # FastAPI REST Routers & Endpoint Controllers
│   │   ├── config.py             # Global Pydantic Settings & Environment Variables
│   │   ├── core/                 # Core Logging, Exceptions, Security & Middleware
│   │   ├── db/                   # MongoDB Connection & Beanie ODM Initialization
│   │   ├── embedding/            # HuggingFace Local Embedding Service (all-MiniLM-L6-v2)
│   │   ├── extraction/           # PDF Document Parsing & Text Chunking Engine
│   │   ├── knowledge_graph/      # Neo4j Driver Connection, Cypher Queries & Graph Builder
│   │   ├── llm/                  # Groq & Ollama Cloud/Local LLM Provider Integrations
│   │   ├── models/               # MongoDB Beanie ODM Data Models
│   │   ├── prompts/              # Engineering Domain Prompt Templates
│   │   ├── rag/                  # Hybrid RAG Context Fusion, Reranking & Confidence Scoring
│   │   ├── schemas/              # Pydantic Request/Response DTO Schemas
│   │   ├── services/             # Core Business Logic & Document Ingestion Services
│   │   └── vectorstore/          # ChromaDB Connection & Semantic Vector Retriever
│   ├── chroma_db/                # Persistent ChromaDB Vector Store (1,066 vectors)
│   ├── uploads/                  # Ingested PDF Document Storage (20 Corpus Papers)
│   ├── tests/                    # Backend Integration & Unit Pytest Suite (86 tests)
│   ├── Dockerfile                # Production Backend Container Manifest
│   ├── pyproject.toml            # Python Project Metadata & Pytest Settings
│   └── requirements.txt          # Frozen Python Dependencies
│
├── frontend/                     # React TypeScript Vite UI Dashboard
│   ├── src/                      # React Components, Pages, Custom Hooks, API Client
│   ├── public/                   # Static Frontend Assets
│   ├── Dockerfile                # Production Frontend Container Manifest
│   ├── package.json              # NPM Package Manifest & Scripts
│   ├── tsconfig.json             # TypeScript Compiler Configuration
│   └── vite.config.ts            # Vite Build Tool Configuration
│
├── scripts/                      # System Workflow & Administration Scripts
│   ├── ingestion/                # OpenAccess Discovery & PDF Corpus Expansion Pipeline
│   ├── benchmark/                # Grounded Benchmark Generation & Ground Truth Validation
│   ├── experiment/               # Five-Architecture Research Experiment Runners & Metric Calculators
│   └── utils/                    # Development Setup & Container Utilities
│
├── experiments/                  # Controlled Research Evaluation Experiments
│   ├── v1/                       # Phase 11 Initial Baseline & Discovery Artifacts
│   ├── v2/                       # Phase 12 Retrieval Metadata Remediation & Pilot Data
│   ├── v3/                       # Phase 13 Frozen 20-Document Corpus & Grounded Benchmark
│   └── v4/                       # Phase 14 / 14.1 Five-Architecture Research Results & Reports
│
├── tests/                        # Comprehensive Test Infrastructure
│   ├── e2e/                      # Playwright End-to-End Browser Workflow Tests
│   └── qa/                       # Master System QA Framework & Failure Analyzer
│
├── docs/                         # Technical & System Documentation
│   ├── API_REFERENCE.md          # Complete REST API Specification
│   └── archive/                  # Historical Phase Audit & Development Reports
│
├── run_smoke_tests.py            # Microservices Health & Port Connectivity Verification
├── run_docker_tests.py           # Docker Container Readiness Validation
└── run_all_tests.py              # Master QA Orchestrator Executing End-to-End Suite
```

## Major Directory Overview

### 1. `backend/`
Contains the complete FastAPI Python backend application. Features stateless hybrid RAG, Neo4j graph traversal, ChromaDB vector retrieval, and a 5-agent orchestration pipeline. Includes full unit & integration pytest suite in `backend/tests/`.

### 2. `frontend/`
Modern React 18 + TypeScript + Vite UI dashboard providing an Engineering Assistant chat interface, interactive Knowledge Graph Explorer, Explainability visualizer, Evaluation Dashboard, and System Health Monitor.

### 3. `scripts/`
Grouped administration and research scripts:
- **`ingestion/`**: OpenAccess paper discovery via ArXiv API, PDF text extraction, and vector/graph indexing.
- **`benchmark/`**: Semi-automated construction and 100% database verification of evidence-grounded benchmark questions.
- **`experiment/`**: Controlled five-architecture RAG research runners, metric calculators, and reproducibility tools.
- **`utils/`**: Utility scripts for environment setup and Docker stack initialization.

### 4. `experiments/`
Contains all frozen research evaluation data, corpus inventories, benchmark ground truth, and five-architecture experiment outputs (`v1` through `v4`).

### 5. `tests/`
Houses non-unit system test suites:
- **`e2e/`**: End-to-end browser user workflow tests using Playwright.
- **`qa/`**: Knowledge base integrity tests, failure classification analysis, and system health checks.

### 6. `docs/`
System documentation, OpenAPI specifications (`API_REFERENCE.md`), and archived phase execution reports.
