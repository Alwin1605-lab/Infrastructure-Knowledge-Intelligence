"""Ollama LLM provider implementation.

Provides LLM capabilities via a locally-running Ollama instance.
Uses the ``langchain-ollama`` integration for both direct generation
and LangChain pipeline compatibility.

Features:
    - Async generation via ``ChatOllama.ainvoke()``.
    - Streaming support via ``ChatOllama.astream()``.
    - Health check against the Ollama REST API (``/api/tags``).
    - Automatic error mapping to application-level exceptions.
"""

import time
from typing import AsyncGenerator

import httpx
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

from app.config import Settings
from app.core.exceptions import (
    LLMConnectionError,
    LLMGenerationError,
)
from app.core.logging import get_logger
from app.llm.base import BaseLLMProvider, LLMResponse
from app.llm.factory import register_provider

logger = get_logger(__name__)


@register_provider("ollama")
class OllamaProvider(BaseLLMProvider):
    """Ollama local LLM provider.

    Connects to a locally-running Ollama server for on-premise, private
    LLM inference. Uses ``langchain-ollama`` as the underlying client for
    both direct calls and LangChain pipeline integration.

    Attributes:
        _base_url: The Ollama server base URL (e.g., ``http://localhost:11434``).
        _model: The Ollama model identifier (e.g., ``llama3.2``).
        _chat_model: Pre-configured ``ChatOllama`` instance.
    """

    def __init__(self, settings: Settings) -> None:
        """Initialize the Ollama provider.

        Args:
            settings: Application settings containing Ollama configuration.
        """
        self._base_url: str = settings.OLLAMA_BASE_URL
        self._model: str = settings.OLLAMA_MODEL

        self._chat_model = ChatOllama(
            base_url=self._base_url,
            model=self._model,
        )

        logger.info(
            "ollama_provider_initialized",
            base_url=self._base_url,
            model=self._model,
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def provider_name(self) -> str:
        """Return the provider name.

        Returns:
            str: Always ``'ollama'``.
        """
        return "ollama"

    @property
    def model_name(self) -> str:
        """Return the active Ollama model name.

        Returns:
            str: The configured Ollama model identifier.
        """
        return self._model

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs,
    ) -> LLMResponse:
        """Generate a single, complete response from the Ollama server.

        Uses ``ChatOllama.ainvoke()`` with a message list built from the
        prompt and optional system prompt.

        Args:
            prompt: The user prompt to send.
            system_prompt: Optional system instruction.
            temperature: Sampling temperature override (applied per-request).
            max_tokens: Max tokens override (applied per-request via ``num_predict``).
            **kwargs: Additional parameters forwarded to ``ainvoke()``.

        Returns:
            LLMResponse: Standardized response with content and metadata.

        Raises:
            LLMConnectionError: When the Ollama server is unreachable.
            LLMGenerationError: For any other generation error.
        """
        messages = self._build_messages(prompt, system_prompt)

        # Apply per-request overrides by creating a bound model copy.
        chat_model = self._get_configured_model(temperature, max_tokens)

        try:
            response = await chat_model.ainvoke(messages, **kwargs)
        except (httpx.ConnectError, httpx.ConnectTimeout, ConnectionError) as exc:
            logger.error(
                "ollama_connection_error",
                base_url=self._base_url,
                model=self._model,
                error=str(exc),
            )
            raise LLMConnectionError(
                provider="ollama",
                message=(
                    f"Failed to connect to Ollama at {self._base_url}: {exc}. "
                    "Ensure the Ollama server is running."
                ),
            ) from exc
        except Exception as exc:
            logger.error(
                "ollama_generation_error",
                model=self._model,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            raise LLMGenerationError(
                provider="ollama",
                message=f"Ollama generation failed: {exc}",
            ) from exc

        # Extract usage metadata from the LangChain response.
        usage_metadata = getattr(response, "usage_metadata", {}) or {}

        return LLMResponse(
            content=response.content or "",
            model=self._model,
            provider="ollama",
            usage={
                "prompt_tokens": usage_metadata.get("input_tokens", 0),
                "completion_tokens": usage_metadata.get("output_tokens", 0),
                "total_tokens": usage_metadata.get("total_tokens", 0),
            },
            finish_reason=response.response_metadata.get("done_reason")
            if hasattr(response, "response_metadata")
            else None,
            raw_response=response.response_metadata
            if hasattr(response, "response_metadata")
            else {},
        )

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response from the Ollama server.

        Uses ``ChatOllama.astream()`` and yields content chunks.

        Args:
            prompt: The user prompt to send.
            system_prompt: Optional system instruction.
            temperature: Sampling temperature override.
            max_tokens: Max tokens override.
            **kwargs: Additional parameters forwarded to ``astream()``.

        Yields:
            str: Individual text chunks of the generated content.

        Raises:
            LLMConnectionError: When the Ollama server is unreachable.
            LLMGenerationError: For any other streaming error.
        """
        messages = self._build_messages(prompt, system_prompt)
        chat_model = self._get_configured_model(temperature, max_tokens)

        try:
            async for chunk in chat_model.astream(messages, **kwargs):
                if chunk.content:
                    yield chunk.content

        except (httpx.ConnectError, httpx.ConnectTimeout, ConnectionError) as exc:
            logger.error(
                "ollama_stream_connection_error",
                base_url=self._base_url,
                model=self._model,
                error=str(exc),
            )
            raise LLMConnectionError(
                provider="ollama",
                message=(
                    f"Failed to connect to Ollama at {self._base_url} "
                    f"during streaming: {exc}. Ensure the Ollama server is running."
                ),
            ) from exc
        except Exception as exc:
            logger.error(
                "ollama_stream_generation_error",
                model=self._model,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            raise LLMGenerationError(
                provider="ollama",
                message=f"Ollama streaming generation failed: {exc}",
            ) from exc

    # ------------------------------------------------------------------
    # LangChain Integration
    # ------------------------------------------------------------------

    def get_langchain_llm(self) -> BaseChatModel:
        """Get a LangChain-compatible ``ChatOllama`` instance.

        Returns the pre-configured ``ChatOllama`` model, suitable for use
        in LangChain chains, LangGraph agents, and RAG pipelines.

        Returns:
            BaseChatModel: The configured ``ChatOllama`` instance.
        """
        return self._chat_model

    # ------------------------------------------------------------------
    # Health Check
    # ------------------------------------------------------------------

    async def health_check(self) -> dict:
        """Check Ollama server connectivity and measure latency.

        Sends an HTTP GET request to ``{base_url}/api/tags`` to verify
        the Ollama server is running and responsive.

        Returns:
            dict: Health status with keys:
                - provider (str): ``'ollama'``.
                - model (str): The configured model.
                - status (str): ``'healthy'`` or ``'unhealthy'``.
                - latency_ms (float): Round-trip latency in milliseconds.
                - error (str, optional): Error message if unhealthy.
                - available_models (list[str], optional): Models loaded in Ollama.
        """
        start_time = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self._base_url}/api/tags")
                response.raise_for_status()

            latency_ms = (time.monotonic() - start_time) * 1000
            data = response.json()

            # Extract available model names from the /api/tags response.
            available_models = [
                model.get("name", "unknown")
                for model in data.get("models", [])
            ]

            logger.debug(
                "ollama_health_check_passed",
                latency_ms=round(latency_ms, 2),
                available_models=available_models,
            )

            return {
                "provider": "ollama",
                "model": self._model,
                "status": "healthy",
                "latency_ms": round(latency_ms, 2),
                "available_models": available_models,
            }
        except Exception as exc:
            latency_ms = (time.monotonic() - start_time) * 1000
            logger.warning(
                "ollama_health_check_failed",
                base_url=self._base_url,
                error=str(exc),
            )
            return {
                "provider": "ollama",
                "model": self._model,
                "status": "unhealthy",
                "latency_ms": round(latency_ms, 2),
                "error": str(exc),
            }

    # ------------------------------------------------------------------
    # Private Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_messages(
        prompt: str,
        system_prompt: str | None = None,
    ) -> list[SystemMessage | HumanMessage]:
        """Build a LangChain message list from prompt and system prompt.

        Args:
            prompt: The user message content.
            system_prompt: Optional system instruction prepended to the
                conversation.

        Returns:
            list: A list of LangChain message objects ready for
                ``ainvoke()`` or ``astream()``.
        """
        messages: list[SystemMessage | HumanMessage] = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))
        return messages

    def _get_configured_model(
        self,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> ChatOllama:
        """Return a ``ChatOllama`` instance with per-request overrides.

        If no overrides are provided, returns the pre-configured model.
        Otherwise, creates a new ``ChatOllama`` with the specified
        temperature and/or ``num_predict`` (Ollama's max-tokens equivalent).

        Args:
            temperature: Optional temperature override.
            max_tokens: Optional max tokens override (mapped to ``num_predict``).

        Returns:
            ChatOllama: A model configured for the current request.
        """
        if temperature is None and max_tokens is None:
            return self._chat_model

        kwargs: dict = {
            "base_url": self._base_url,
            "model": self._model,
        }
        if temperature is not None:
            kwargs["temperature"] = temperature
        if max_tokens is not None:
            kwargs["num_predict"] = max_tokens

        return ChatOllama(**kwargs)
