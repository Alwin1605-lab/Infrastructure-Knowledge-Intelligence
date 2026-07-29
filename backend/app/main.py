"""FastAPI application factory.

Creates and configures the FastAPI application with:
- Lifespan management (startup/shutdown)
- CORS middleware
- Global exception handlers
- API router mounting
"""

import contextlib
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.core.exceptions import InfraKnowledgeError
from app.db.connection import init_db, close_db
from app.vectorstore.connection import init_vectorstore, close_vectorstore
from app.knowledge_graph.connection import init_kg, close_kg
from app.api.v1.router import api_v1_router

logger = get_logger(__name__)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan - startup and shutdown events.

    Handles initialization of shared services on startup and
    graceful cleanup on shutdown.

    Startup:
        - Configures structured logging
        - Initializes the LLM provider (stored in app.state)
        - Initializes the embedding service (stored in app.state)
        - Creates the uploads directory

    Shutdown:
        - Logs shutdown event

    Args:
        app: The FastAPI application instance.

    Yields:
        None: Control is yielded to the application after startup completes.
    """
    settings = get_settings()

    # --- Startup ---
    setup_logging(debug=settings.DEBUG)
    logger.info("application_starting", app_name=settings.APP_NAME, env=settings.APP_ENV)

    # Initialize LLM provider (stored in app.state)
    from app.llm import create_llm_provider
    app.state.llm_provider = create_llm_provider(settings)
    logger.info("llm_provider_initialized", provider=app.state.llm_provider.provider_name)

    # Initialize Embedding service
    from app.embedding import HuggingFaceEmbeddingService
    app.state.embedding_service = HuggingFaceEmbeddingService(settings)
    logger.info("embedding_service_initialized", model=settings.EMBEDDING_MODEL)

    # Initialize MongoDB + Beanie ODM
    try:
        await init_db(settings)
        logger.info("mongodb_initialized")
    except Exception as exc:
        logger.warning("mongodb_init_failed", error=str(exc),
                       note="App will start but document features require MongoDB")

    # Initialize ChromaDB vector store
    try:
        chroma_client = await init_vectorstore(settings)
        app.state.chroma_client = chroma_client
        logger.info("vectorstore_initialized", collection=settings.CHROMADB_COLLECTION)
    except Exception as exc:
        logger.warning("vectorstore_init_failed", error=str(exc),
                       note="App will start but RAG requires ChromaDB")
        app.state.chroma_client = None

    # Initialize Neo4j Knowledge Graph
    try:
        await init_kg(settings)
        logger.info("knowledge_graph_initialized")
    except Exception as exc:
        logger.warning("knowledge_graph_init_failed", error=str(exc),
                       note="App will start but Knowledge Graph features require Neo4j")

    # Initialize Hybrid RAG Pipeline (Phase 5)
    try:
        from app.services.rag_service import RAGService
        app.state.rag_service = RAGService(
            llm_provider=app.state.llm_provider,
            embedding_service=app.state.embedding_service,
        )
        logger.info("rag_pipeline_initialized")
    except Exception as exc:
        logger.warning("rag_pipeline_init_failed", error=str(exc),
                       note="App will start but /chat endpoints require RAG pipeline")
        app.state.rag_service = None

    # Initialize Agentic AI Pipeline (Phase 6)
    try:
        from app.services.agent_service import AgentService
        app.state.agent_service = AgentService(
            llm_provider=app.state.llm_provider,
            embedding_service=app.state.embedding_service,
        )
        logger.info("agent_pipeline_initialized")
    except Exception as exc:
        logger.warning("agent_pipeline_init_failed", error=str(exc),
                       note="App will start but /agents endpoints require AgentService")
        app.state.agent_service = None

    # Initialize Evaluation Framework (Phase 7)
    try:
        from app.services.evaluation_service import EvaluationService
        app.state.evaluation_service = EvaluationService(
            llm_provider=app.state.llm_provider,
            rag_service=app.state.rag_service,
            agent_service=app.state.agent_service,
        )
        logger.info("evaluation_framework_initialized")
    except Exception as exc:
        logger.warning("evaluation_framework_init_failed", error=str(exc),
                       note="App will start but /eval endpoints require EvaluationService")
        app.state.evaluation_service = None

    # Create uploads directory
    import os
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    logger.info("application_started")
    
    # --- Startup Validation Summary ---
    from app.api.v1.health import get_system_health
    from fastapi import Request
    
    # Create a mock request to pass to the health check function
    class MockApp:
        def __init__(self, state):
            self.state = state
    class MockRequest:
        def __init__(self, app_state):
            self.app = MockApp(app_state)
            
    health_data = await get_system_health(MockRequest(app.state))
    
    print("\n" + "="*40)
    print("Building Knowledge Intelligence System")
    print(f"Version: {health_data.versions.get('backend_version', '0.9.0')}")
    print("")
    
    def format_status(service_name, dict_key):
        status = health_data.services.get(dict_key)
        icon = "✓" if status == "ok" else "✗"
        return f"{service_name:<12} {icon} {'Connected/Ready' if status == 'ok' else 'Disconnected/Down'}"
        
    print(format_status("MongoDB", "mongodb"))
    print(format_status("Neo4j", "neo4j"))
    print(format_status("ChromaDB", "chromadb"))
    print(format_status("Groq", "groq_llm"))
    print("")
    print(f"Documents Indexed: {health_data.knowledge_base.get('documents_indexed', 0)}")
    print(f"Knowledge Graph Nodes: {health_data.knowledge_base.get('kg_nodes', 0)}")
    print(f"Relationships: {health_data.knowledge_base.get('kg_relationships', 0)}")
    print("="*40 + "\n")

    yield

    # --- Shutdown ---
    logger.info("application_shutting_down")
    await close_db()
    await close_vectorstore()
    await close_kg()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Builds the FastAPI instance with all middleware, exception handlers,
    and routers configured. This factory pattern allows for easy testing
    and multiple application instances.

    Returns:
        FastAPI: The fully configured application instance.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        description=(
            "AI-Driven Decision Support System for Building Maintenance and Structural "
            "Assessment using Knowledge Graphs, Hybrid RAG, Groq LLM, and a 5-Agent "
            "Agentic AI Pipeline. "
            "Domain: RCC Buildings, Residential, Commercial, Institutional, and Government Structures. "
            "\n\n**Phase 5**: Hybrid RAG Pipeline — POST /api/v1/chat/query"
            "\n\n**Phase 6**: Agentic AI Pipeline — POST /api/v1/agents/query (with per-agent reason + confidence)"
            "\n\n**Phase 7**: Evaluation Framework — POST /api/v1/eval/benchmark (Benchmarking & Explainability)"
        ),
        version="0.7.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global exception handler
    @app.exception_handler(InfraKnowledgeError)
    async def infra_knowledge_error_handler(request: Request, exc: InfraKnowledgeError):
        """Handle all InfraKnowledgeError exceptions with structured JSON responses.

        Args:
            request: The incoming HTTP request.
            exc: The raised InfraKnowledgeError instance.

        Returns:
            JSONResponse: A JSON error response with the error type and message.
        """
        logger.error("application_error", error=str(exc), error_type=type(exc).__name__)
        return JSONResponse(
            status_code=500,
            content={"error": type(exc).__name__, "message": exc.message},
        )

    # Mount API router
    app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

    return app


# Application instance
app = create_app()
