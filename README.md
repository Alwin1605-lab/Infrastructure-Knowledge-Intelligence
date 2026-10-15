# Building Knowledge Intelligence System

An AI-driven decision-support platform for structural condition assessment, defect diagnosis, and maintenance planning. The system combines Knowledge Graphs (Neo4j), Dense Vector Search (ChromaDB), and an autonomous 5-Agent Pipeline orchestrating Llama 3 models via the Groq Cloud API.

---

## 🏛️ System Architecture

```mermaid
graph TD
    User([Structural Engineer / Admin]) --> |Interactive Web UI| Frontend[React 18 + Vite Frontend :5173]
    Frontend --> |REST API / JWT Auth| Backend[FastAPI Backend :8000]
    
    subgraph Knowledge Base Layer
        Extractor[PDF Parser & Entity Extractor]
        ChromaDB[(ChromaDB Vector Store :8000)]
        Neo4j[(Neo4j Knowledge Graph :7687)]
        MongoDB[(MongoDB Document & User Store :27017)]
    end
    
    Backend --> Extractor
    Extractor --> |Semantic Embeddings (all-MiniLM-L6-v2)| ChromaDB
    Extractor --> |Ontology Triples (7 Entity Types)| Neo4j
    Extractor --> |Document Metadata & Jobs| MongoDB
    
    subgraph Multi-Agent Orchestration Pipeline
        Orchestrator{Agent Orchestrator}
        QAgent[1. Query Analysis Agent]
        RAgent[2. Retrieval Agent]
        KGBAgent[3. KG Reasoning Agent]
        RecAgent[4. Recommendation Agent]
        RepAgent[5. Report Generation Agent]
    end
    
    Backend --> Orchestrator
    Orchestrator --> QAgent --> RAgent --> KGBAgent --> RecAgent --> RepAgent
    
    RAgent -.-> |Dense Semantic Search| ChromaDB
    KGBAgent -.-> |Multi-Hop Cypher Traversal| Neo4j
    
    Orchestrator --> Groq[Groq LPU Engine / Llama 3]
```

---

## ✨ Key Features & Capabilities

* **5-Agent Autonomous Pipeline:** Sequential state-graph orchestration (`QueryAnalysisAgent` $\rightarrow$ `RetrievalAgent` $\rightarrow$ `KGReasoningAgent` $\rightarrow$ `RecommendationAgent` $\rightarrow$ `ReportAgent`) with natural language reasoning traces and confidence scoring.
* **Hybrid Graph-RAG:** Reciprocal-rank context fusion combining ChromaDB cosine vector chunks with Neo4j causal subgraphs (`Defect` $\rightarrow$ `CAUSED_BY` $\rightarrow$ `Cause` $\rightarrow$ `AFFECTS` $\rightarrow$ `Component` $\rightarrow$ `REPAIRED_BY` $\rightarrow$ `RepairMethod`).
* **Multi-Format Deliverable Export:** Instant export of comprehensive structural assessment reports to **Printable PDF (`.pdf`)**, **Microsoft Word (`.docx` / `.doc`)**, and **Markdown (`.md`)**.
* **Live Knowledge Base & Document Library:** Ingests multi-page engineering PDFs, tracks live chunking/KG extraction progress, and searches indexed codes (IS 456, NBC 2016, CPWD).
* **Research Benchmarking & Explainability:** Evaluates 105 ground-truth questions across 5 architectures with quantitative metrics (Hit Rate@5: 100%, Citation Rate: 100%, MRR: 1.0).
* **Dark / Light Theme Engine:** Smooth theme switching with full persistent preferences.

---

## 🔑 Default Login Credentials

| Role | Email | Password | Access Scope |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin@example.com` | `password123` | Full access (Document Upload, Queue, Dev Mode, Analytics) |
| **Administrator** | `admin@buildknowledge.ai` | `admin123` | Secondary Admin Account |
| **Structural Engineer** | `engineer@example.com` | `password123` | Analysis Workspace, Reports, Standards Library |

---

## 🚀 How to Run the Project

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (running)
- Python 3.11 or 3.12
- Node.js 18+ or 20+ & npm
- A Groq API Key (Free tier from [console.groq.com](https://console.groq.com))

---

### Option A: Quick Start via Docker Compose (Recommended)

1. **Clone and Navigate:**
   ```bash
   git clone https://github.com/Alwin1605-lab/Infrastructure-Knowledge-Intelligence.git
   cd Infrastructure-Knowledge-Intelligence
   ```

2. **Configure Environment:**
   Ensure `.env` exists in the root directory:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   LLM_PROVIDER=groq
   GROQ_MODEL=groq/compound-mini
   SECRET_KEY=your_jwt_secret_key_here
   ```

3. **Build & Start All Containers:**
   ```bash
   docker-compose up -d --build
   ```

4. **Verify Health:**
   ```bash
   python run_smoke_tests.py
   ```

---

### Option B: Local Development Setup (Fast & Interactive)

If you prefer running the backend and frontend locally with live hot-reloading:

#### 1. Start Database Containers in Docker
```bash
docker start infra_mongodb infra_neo4j infra_chromadb
```
*(Or run `docker-compose up -d mongodb neo4j chromadb`)*

#### 2. Start the FastAPI Backend
In a terminal:
```bash
cd backend
python -m venv venv
venv\Scripts\activate          # On Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 3. Start the React Frontend
In a separate terminal:
```bash
cd frontend
npm install
npm run dev
```

---

## 🌐 Service Access URLs

| Service / Interface | URL | Description |
| :--- | :--- | :--- |
| **Frontend Web App** | [http://localhost:5173](http://localhost:5173) | Main UI (Assistant, KG Explorer, Documents, Analytics) |
| **Backend API Docs** | [http://localhost:8000/docs](http://localhost:8000/docs) | Interactive Swagger / OpenAPI Specification |
| **System Health API** | [http://localhost:8000/api/v1/health/system](http://localhost:8000/api/v1/health/system) | Real-time microservice health & database metrics |
| **Neo4j Browser** | [http://localhost:7474](http://localhost:7474) | Graph Database Visualizer (`bolt://localhost:7687`) |

---

## 🧪 Testing & Verification

Run the comprehensive test suite:

```bash
# 1. Run all 86 backend unit & integration tests
pytest backend/tests

# 2. Run system smoke tests (verifies Frontend, Backend, Mongo, Neo4j)
python run_smoke_tests.py

# 3. Test frontend production build
cd frontend && npm run build
```

---

## 📁 Repository Structure

```text
├── backend/                  # FastAPI Python Application
│   ├── app/
│   │   ├── agents/           # 5-Agent State Graph Orchestrator
│   │   ├── api/v1/           # REST API Route Controllers
│   │   ├── embedding/        # HuggingFace all-MiniLM-L6-v2 Embeddings
│   │   ├── knowledge_graph/  # Neo4j Driver, Cypher Queries & Ontologies
│   │   ├── llm/              # Groq & Ollama LLM Providers
│   │   ├── models/           # Beanie ODM MongoDB Schemas
│   │   ├── prompts/          # Domain Extraction & Recommendation Prompts
│   │   └── rag/              # ChromaDB Retrieval & Context Fusion
│   └── tests/                # 86 Pytest Test Cases
│
├── frontend/                 # React 18 + Vite TypeScript/JavaScript UI
│   ├── src/
│   │   ├── components/       # UI Cards, Modals, Panels, Navbars
│   │   ├── pages/            # Assistant, Library, Analytics, Dev Dashboards
│   │   └── store/            # Zustand State & Dark Theme Store
│   ├── nginx.conf            # Production Nginx Reverse Proxy
│   └── Dockerfile            # Multi-stage Frontend Container
│
├── experiments/              # Phase 14 & 14.1 525-Run Benchmark Results & Reports
├── scripts/                  # Modular Ingestion, Benchmark, and Setup Scripts
│   ├── ingestion/            # PDF Ingestion & Admin Seeders
│   ├── benchmark/            # Benchmark Construction Utilities
│   └── experiment/           # 5-Architecture Experiment Runners
├── docker-compose.yml        # Multi-Container Deployment Orchestration
└── PROJECT_STRUCTURE.md      # Detailed Architecture Directory Map
```

---

## 📄 License & Academic Attribution
Developed as part of the **Building Knowledge Intelligence System** research initiative. Open Access research documents and standards are cited under their respective fair-use and academic licenses.
