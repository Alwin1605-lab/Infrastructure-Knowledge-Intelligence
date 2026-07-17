# 🏢 Building Knowledge Intelligence

**An AI-Driven Decision Support System Using Knowledge Graphs, Retrieval-Augmented Generation (RAG), Large Language Models, and Agentic AI for Building Maintenance and Structural Decision Support.**

---

## 📋 Overview

Building Knowledge Intelligence is a full-stack AI-powered platform that serves as a **virtual building engineering assistant** for civil engineers, building inspectors, and facility managers. The system focuses exclusively on **buildings** — reinforced concrete (RCC), residential, commercial, institutional, and government structures.

The platform enables professionals to:

- **Upload & Process** building engineering documents (PDF inspection reports, CPWD manuals, structural audit reports, BIS standards)
- **Build a Building Knowledge Graph** automatically from extracted content using Neo4j
- **Semantic Search** across all uploaded documents using vector embeddings and ChromaDB
- **Ask Questions** using a hybrid RAG pipeline that fuses knowledge graph context with semantic retrieval
- **Analyze Building Defects** with root cause identification and engineering recommendations
- **Generate Professional Reports** (Building Inspection Report, Condition Assessment, Maintenance Recommendation Report, Structural Defect Analysis)

### Knowledge Domain

| Category | Examples |
|---|---|
| **Building Components** | Foundation, Footing, Column, Beam, Slab, Wall, Roof, Staircase |
| **Building Defects** | Cracks, Spalling, Honeycombing, Corrosion, Water Seepage, Efflorescence, Settlement |
| **Root Causes** | Poor Workmanship, Improper Curing, Water Ingress, Overloading, Design Errors, Aging |
| **Repair Methods** | Epoxy Injection, Concrete Jacketing, Waterproofing, Grouting, Structural Strengthening |

### Primary Knowledge Sources

- CPWD Maintenance Manual
- CPWD Handbook on Repairs & Rehabilitation of RCC Buildings
- CPWD Works Manual & Quality Assurance Manual
- National Building Code (NBC)
- BIS Standards (IS codes)
- Building Structural Audit Reports & Inspection Reports

---

## 🛠️ Tech Stack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **LLM Providers**: Groq (cloud, free tier) / Ollama (local, offline)
- **Embeddings**: HuggingFace Sentence Transformers `all-MiniLM-L6-v2` (local, no API key)
- **Orchestration**: LangChain + LangGraph (multi-agent workflow)

### Databases
- **Document Store**: MongoDB 7 (via Motor + Beanie ODM)
- **Knowledge Graph**: Neo4j 5 (Building entities: Component, Defect, Cause, RepairMethod, Risk, Material)
- **Vector Store**: ChromaDB (semantic similarity over building documents)

### Frontend
- **Framework**: React 18+ with Vite
- **KG Visualization**: react-force-graph-2d
- **Styling**: Modern CSS with responsive design

### Infrastructure
- **Containerization**: Docker & Docker Compose
- **Logging**: Structlog (structured JSON logging)

---

## 🏛️ Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│           Frontend (React + Vite)                         │
│   Chat UI · Document Upload · Building KG Viewer         │
└─────────────────────┬────────────────────────────────────┘
                      │ REST API
┌─────────────────────▼────────────────────────────────────┐
│                   FastAPI Backend                          │
│  ┌───────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ Document  │  │  Building    │  │ Report Generator  │  │
│  │ Pipeline  │  │ RAG Pipeline │  │ (CPWD-aligned)    │  │
│  └─────┬─────┘  └──────┬───────┘  └───────────────────┘  │
│        │               │                                   │
│  ┌─────▼───────────────▼──────────────────────────────┐   │
│  │             LangGraph Multi-Agent System            │   │
│  │  Retrieval → Building Reasoning → Recommendation   │   │
│  │         → Engineering Report Generator             │   │
│  └────────────────────────────────────────────────────┘   │
│  ┌────────────────────────────────────────────────────┐   │
│  │              LLM Provider Layer                    │   │
│  │       Groq (cloud) ←→ Ollama (local)              │   │
│  └────────────────────────────────────────────────────┘   │
└───────┬──────────────┬──────────────┬─────────────────────┘
        │              │              │
┌───────▼────┐ ┌───────▼────┐ ┌──────▼──────┐
│  MongoDB   │ │   Neo4j    │ │  ChromaDB   │
│(Doc Store) │ │ (Building  │ │  (Building  │
│            │ │   KG)      │ │  Vectors)   │
└────────────┘ └────────────┘ └─────────────┘
```

### Building Knowledge Graph Structure

```
Building
  └── Contains → Component (Column / Beam / Slab / Wall / Roof / Foundation)
        └── Has Defect → Defect (Spalling / Cracks / Seepage / Honeycombing)
              ├── Caused By → Cause (Corrosion / Poor Curing / Overloading)
              └── Repaired By → RepairMethod (Epoxy Injection / Concrete Jacketing)
```

---

## 📌 Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| Python | ≥ 3.11 | Backend runtime |
| Node.js | ≥ 20 | Frontend build toolchain |
| Docker | Latest | Database services |
| Docker Compose | ≥ 2.0 | Multi-container orchestration |
| Git | Latest | Version control |

---

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/building-knowledge-intelligence.git
cd building-knowledge-intelligence
```

### 2. Environment Setup

```bash
cp .env.example .env
# Edit .env and add your Groq API key
```

### 3. Start Database Services

```bash
docker-compose up -d
docker-compose ps   # Verify all services are healthy
```

### 4. Start the Backend

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API available at `http://localhost:8000` · Docs at `http://localhost:8000/docs`

### 5. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend available at `http://localhost:5173`.

---

## 📁 Project Structure

```
building-knowledge-intelligence/
├── .env.example              # Environment variable template
├── docker-compose.yml        # Database services (MongoDB, Neo4j, ChromaDB)
├── README.md                 # This file
│
├── backend/
│   ├── requirements.txt      # Python dependencies
│   ├── app/
│   │   ├── main.py           # FastAPI application entry point
│   │   ├── config.py         # Centralized configuration
│   │   ├── prompts/          # ★ All LLM prompts (building domain)
│   │   ├── evaluation/       # ★ Research evaluation metrics
│   │   ├── llm/              # LLM provider abstraction (Groq / Ollama)
│   │   ├── embedding/        # HuggingFace all-MiniLM-L6-v2 (local)
│   │   ├── db/               # MongoDB models + repositories
│   │   ├── models/           # Beanie ODM document models
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   ├── services/         # Business logic (Document, RAG, KG, Report)
│   │   ├── agents/           # LangGraph multi-agent system
│   │   ├── knowledge_graph/  # Neo4j building KG
│   │   ├── vectorstore/      # ChromaDB building document vectors
│   │   ├── api/              # FastAPI route handlers
│   │   ├── core/             # Exceptions + structured logging
│   │   └── utils/            # PDF parser, text splitter, file handler
│
└── frontend/
    ├── src/
    │   ├── components/       # Reusable UI components
    │   ├── pages/            # Dashboard, Documents, Chat, KG, Reports
    │   └── store/            # Zustand state management
```

---

## 📄 License

This project is licensed under the MIT License.

---

<p align="center">
  Built with ❤️ for building engineering professionals · B.Tech AI & Data Science Final Year Project
</p>
