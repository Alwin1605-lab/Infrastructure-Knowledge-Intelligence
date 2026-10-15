# Project Structure
## Backend (`/backend`)
- `app/api/`: FastAPI route handlers (v1).
- `app/services/`: Core business logic (RAG, KG, Documents, Analytics).
- `app/agents/`: LangGraph/LangChain agentic workflows.
- `app/models/`: Beanie ODM definitions.
- `scripts/`: Benchmark, Evaluation, and Acquisition scripts.

## Frontend (`/frontend`)
- `src/components/`: Reusable UI components.
- `src/pages/`: Lazy-loaded React views.
- `src/api/`: Axios client definitions.
- `src/context/`: Auth and Theme context providers.
