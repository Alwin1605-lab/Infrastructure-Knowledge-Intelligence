"""HuggingFace embedding service using sentence-transformers.

Provides local embedding generation via the all-MiniLM-L6-v2 model
(or configured alternative). No API keys or external services required.

The model is lazily loaded on first use to avoid slow startup times.
All HuggingFace operations are run in a thread executor to maintain
async compatibility.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from app.core.exceptions import EmbeddingError, EmbeddingModelLoadError
from app.core.logging import get_logger

if TYPE_CHECKING:
    from langchain_huggingface import HuggingFaceEmbeddings

    from app.config import Settings

logger = get_logger(__name__)


class HuggingFaceEmbeddingService:
    """Local embedding service using HuggingFace sentence-transformers.

    Generates dense vector embeddings for text using a locally-loaded
    sentence-transformer model. The default model (all-MiniLM-L6-v2)
    produces 384-dimensional vectors optimized for semantic similarity.

    The model is lazily loaded on first use: instantiation is cheap,
    and the actual model download/load only happens when an embedding
    operation is first requested.

    Attributes:
        model_name: Name of the HuggingFace model to use.
        device: Device to run the model on (e.g. ``"cpu"``, ``"cuda"``).

    Example:
        >>> from app.config import get_settings
        >>> service = HuggingFaceEmbeddingService(get_settings())
        >>> vectors = await service.embed_documents(["bridge deck", "rebar corrosion"])
        >>> len(vectors[0])
        384
    """

    # Default embedding dimension for all-MiniLM-L6-v2.
    _DEFAULT_DIMENSION: int = 384

    def __init__(self, settings: Settings) -> None:
        """Initialize the embedding service.

        Stores configuration from *settings* but does **not** load the
        model. Model loading is deferred to the first call that needs it.

        Args:
            settings: Application settings containing ``EMBEDDING_MODEL``
                and ``EMBEDDING_DEVICE`` fields.
        """
        self.model_name: str = settings.EMBEDDING_MODEL
        self.device: str = settings.EMBEDDING_DEVICE
        self._model: HuggingFaceEmbeddings | None = None

        logger.info(
            "HuggingFaceEmbeddingService initialized (model=%s, device=%s). "
            "Model will be loaded on first use.",
            self.model_name,
            self.device,
        )

    def _load_model(self) -> None:
        """Lazily load the sentence-transformer model.

        Downloads (if necessary) and loads the configured HuggingFace
        model into memory. This is called automatically on first use
        and should not normally be invoked directly.

        Raises:
            EmbeddingModelLoadError: If the model cannot be loaded for
                any reason (missing package, download failure, OOM, etc.).
        """
        if self._model is not None:
            return

        logger.info(
            "Loading embedding model '%s' on device '%s' …",
            self.model_name,
            self.device,
        )

        try:
            from langchain_huggingface import HuggingFaceEmbeddings

            # Try loading from local cache first to avoid slow network timeouts/retries
            try:
                self._model = HuggingFaceEmbeddings(
                    model_name=self.model_name,
                    model_kwargs={"device": self.device, "local_files_only": True},
                    encode_kwargs={"normalize_embeddings": True},
                )
            except Exception:
                logger.info(
                    "Model '%s' not cached locally (or local load failed); downloading from HuggingFace Hub …",
                    self.model_name,
                )
                self._model = HuggingFaceEmbeddings(
                    model_name=self.model_name,
                    model_kwargs={"device": self.device, "local_files_only": False},
                    encode_kwargs={"normalize_embeddings": True},
                )

            logger.info(
                "Embedding model '%s' loaded successfully on '%s'.",
                self.model_name,
                self.device,
            )
        except Exception as exc:
            logger.error(
                "Failed to load embedding model '%s': %s",
                self.model_name,
                exc,
            )
            raise EmbeddingModelLoadError(
                f"Could not load embedding model '{self.model_name}': {exc}"
            ) from exc

    def _ensure_model_loaded(self) -> None:
        """Ensure the model is loaded, triggering lazy load if needed."""
        if self._model is None:
            self._load_model()

    # ------------------------------------------------------------------
    # Public async API
    # ------------------------------------------------------------------

    async def embed_text(self, text: str) -> list[float]:
        """Embed a single text string into a dense vector.

        The embedding operation is offloaded to a thread executor because
        the underlying HuggingFace model is synchronous.

        Args:
            text: The text to embed. Should be a non-empty string.

        Returns:
            A list of floats representing the embedding vector.

        Raises:
            EmbeddingError: If embedding generation fails.
        """
        if not text or not text.strip():
            raise EmbeddingError("Cannot embed empty or whitespace-only text.")

        self._ensure_model_loaded()

        try:
            loop = asyncio.get_event_loop()
            vector: list[float] = await loop.run_in_executor(
                None,
                self._model.embed_query,  # type: ignore[union-attr]
                text,
            )
            return vector
        except EmbeddingError:
            raise
        except Exception as exc:
            logger.error("Failed to embed text: %s", exc)
            raise EmbeddingError(
                f"Embedding generation failed for text: {exc}"
            ) from exc

    async def embed_documents(self, documents: list[str]) -> list[list[float]]:
        """Embed multiple documents into dense vectors.

        All documents are embedded in a single batch call, offloaded to
        a thread executor for async compatibility.

        Args:
            documents: List of text strings to embed.

        Returns:
            List of embedding vectors, one per input document. Each
            vector is a list of floats.

        Raises:
            EmbeddingError: If embedding generation fails.
        """
        if not documents:
            return []

        self._ensure_model_loaded()

        try:
            loop = asyncio.get_event_loop()
            vectors: list[list[float]] = await loop.run_in_executor(
                None,
                self._model.embed_documents,  # type: ignore[union-attr]
                documents,
            )
            return vectors
        except Exception as exc:
            logger.error("Failed to embed %d documents: %s", len(documents), exc)
            raise EmbeddingError(
                f"Batch embedding generation failed for {len(documents)} documents: {exc}"
            ) from exc

    def get_langchain_embeddings(self) -> HuggingFaceEmbeddings:
        """Return the underlying LangChain embeddings instance.

        Useful when integrating with LangChain chains, vector stores,
        or retrievers that expect an ``Embeddings`` object.

        Returns:
            The :class:`HuggingFaceEmbeddings` instance.

        Raises:
            EmbeddingModelLoadError: If the model cannot be loaded.
        """
        self._ensure_model_loaded()
        assert self._model is not None  # noqa: S101 – guarded by _ensure_model_loaded
        return self._model

    async def health_check(self) -> dict[str, str | int]:
        """Return the health status of the embedding service.

        Can be called without the model being loaded—in that case,
        the status will reflect that the model is not yet loaded.

        Returns:
            Dict with keys ``model_name``, ``status``,
            ``embedding_dimension``, and ``device``.
        """
        status: str
        if self._model is not None:
            status = "loaded"
        else:
            status = "not_loaded"

        return {
            "model_name": self.model_name,
            "status": status,
            "embedding_dimension": self._DEFAULT_DIMENSION,
            "device": self.device,
        }
