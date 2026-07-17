"""Custom exception classes for the application.

All custom exceptions inherit from InfraKnowledgeError.
This hierarchy enables granular error handling throughout the application.

Exception Hierarchy:
    InfraKnowledgeError
    ├── LLMProviderError
    │   ├── LLMConnectionError
    │   ├── LLMRateLimitError
    │   ├── LLMGenerationError
    │   └── LLMConfigurationError
    ├── UnsupportedProviderError
    ├── EmbeddingError
    │   └── EmbeddingModelLoadError
    ├── DocumentError
    │   ├── DocumentNotFoundError
    │   ├── DocumentExtractionError
    │   └── DocumentUploadError
    ├── KnowledgeGraphError
    │   ├── KGConnectionError
    │   ├── KGBuildError
    │   └── KGQueryError
    ├── RAGError
    │   ├── RetrievalError
    │   └── ContextFusionError
    ├── ReportGenerationError
    └── VectorStoreError
        ├── VectorStoreConnectionError
        └── VectorStoreIndexError
"""


class InfraKnowledgeError(Exception):
    """Base exception for all application errors.

    All custom exceptions in this project should inherit from this class.
    This allows catching all application-specific errors with a single
    except clause when needed.
    """

    def __init__(self, message: str = "An unexpected error occurred", *args, **kwargs):
        self.message = message
        super().__init__(message, *args, **kwargs)


# =============================================================================
# LLM Provider Errors
# =============================================================================


class LLMProviderError(InfraKnowledgeError):
    """Base exception for LLM provider errors.

    Attributes:
        provider: The name of the LLM provider that caused the error.
    """

    def __init__(self, provider: str, message: str, *args, **kwargs):
        self.provider = provider
        super().__init__(f"[{provider}] {message}", *args, **kwargs)


class LLMConnectionError(LLMProviderError):
    """Raised when connection to LLM provider fails.

    This can occur when the provider's API is unreachable,
    the network is down, or the service is temporarily unavailable.
    """

    pass


class LLMRateLimitError(LLMProviderError):
    """Raised when LLM provider rate limit is exceeded.

    Attributes:
        retry_after: Suggested wait time in seconds before retrying, if provided.
    """

    def __init__(self, provider: str, retry_after: float | None = None, *args, **kwargs):
        self.retry_after = retry_after
        msg = "Rate limit exceeded"
        if retry_after:
            msg += f" (retry after {retry_after}s)"
        super().__init__(provider, msg, *args, **kwargs)


class LLMGenerationError(LLMProviderError):
    """Raised when LLM text generation fails.

    This can occur due to invalid prompts, content filtering,
    or internal provider errors during generation.
    """

    pass


class LLMConfigurationError(LLMProviderError):
    """Raised when LLM provider is misconfigured.

    Common causes: missing API key, invalid model name,
    or unsupported configuration parameters.
    """

    pass


class UnsupportedProviderError(InfraKnowledgeError):
    """Raised when an unsupported LLM provider is requested.

    Attributes:
        provider: The unsupported provider name that was requested.
        supported: List of supported provider names.
    """

    def __init__(self, provider: str, supported: list[str], *args, **kwargs):
        self.provider = provider
        self.supported = supported
        super().__init__(
            f"Unsupported LLM provider: '{provider}'. Supported: {supported}",
            *args,
            **kwargs,
        )


# =============================================================================
# Embedding Errors
# =============================================================================


class EmbeddingError(InfraKnowledgeError):
    """Raised when embedding generation fails.

    This can occur during text-to-vector conversion using
    the sentence-transformers model.
    """

    pass


class EmbeddingModelLoadError(EmbeddingError):
    """Raised when the embedding model fails to load.

    Common causes: model not found, insufficient memory,
    or corrupted model files.
    """

    pass


# =============================================================================
# Document Errors
# =============================================================================


class DocumentError(InfraKnowledgeError):
    """Base exception for document-related errors."""

    pass


class DocumentNotFoundError(DocumentError):
    """Raised when a requested document is not found.

    Attributes:
        document_id: The ID of the document that was not found.
    """

    def __init__(self, document_id: str, *args, **kwargs):
        self.document_id = document_id
        super().__init__(f"Document not found: {document_id}", *args, **kwargs)


class DocumentExtractionError(DocumentError):
    """Raised when text extraction from a document fails.

    This can occur when processing corrupted, encrypted,
    or unsupported document formats.
    """

    pass


class DocumentUploadError(DocumentError):
    """Raised when document upload fails.

    Common causes: file too large, unsupported format,
    or storage write failure.
    """

    pass


# =============================================================================
# Knowledge Graph Errors
# =============================================================================


class KnowledgeGraphError(InfraKnowledgeError):
    """Base exception for knowledge graph errors."""

    pass


class KGConnectionError(KnowledgeGraphError):
    """Raised when connection to Neo4j fails.

    This can occur when Neo4j is not running, credentials are
    invalid, or the network is unreachable.
    """

    pass


class KGBuildError(KnowledgeGraphError):
    """Raised when knowledge graph construction fails.

    This can occur during entity extraction, relationship mapping,
    or graph write operations.
    """

    pass


class KGQueryError(KnowledgeGraphError):
    """Raised when a knowledge graph query fails.

    This can occur due to invalid Cypher syntax, timeout,
    or graph traversal errors.
    """

    pass


# =============================================================================
# RAG Errors
# =============================================================================


class RAGError(InfraKnowledgeError):
    """Base exception for RAG pipeline errors."""

    pass


class RetrievalError(RAGError):
    """Raised when document retrieval fails.

    This can occur during vector similarity search
    or knowledge graph traversal in the retrieval step.
    """

    pass


class ContextFusionError(RAGError):
    """Raised when context fusion (KG + vector) fails.

    This occurs when combining results from the knowledge graph
    and vector store into a unified context for the LLM.
    """

    pass


# =============================================================================
# Report Errors
# =============================================================================


class ReportGenerationError(InfraKnowledgeError):
    """Raised when report generation fails.

    This can occur during PDF/DOCX generation, template rendering,
    or data aggregation for the report.
    """

    pass


# =============================================================================
# Vector Store Errors
# =============================================================================


class VectorStoreError(InfraKnowledgeError):
    """Base exception for vector store errors."""

    pass


class VectorStoreConnectionError(VectorStoreError):
    """Raised when connection to ChromaDB fails.

    This can occur when ChromaDB is not running or
    the configured host/port is unreachable.
    """

    pass


class VectorStoreIndexError(VectorStoreError):
    """Raised when indexing into the vector store fails.

    This can occur during document chunk insertion,
    embedding storage, or collection management.
    """

    pass
