"""Groq LLM provider implementation.

Provides LLM capabilities via the Groq cloud API, which offers
high-speed inference for open-source models (Llama, Mixtral, etc.).

Features:
    - Async generation with the ``groq`` Python SDK.
    - Automatic retry with exponential backoff for rate-limit errors.
    - Streaming support for real-time response delivery.
    - LangChain integration via ``langchain-groq``.
    - Structured error mapping to application-level exceptions.
"""

import time
from typing import AsyncGenerator

from groq import (
    AsyncGroq,
    APIConnectionError,
    RateLimitError,
    APIStatusError,
)
from langchain_groq import ChatGroq
from langchain_core.language_models import BaseChatModel
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.config import Settings
from app.core.exceptions import (
    LLMConfigurationError,
    LLMConnectionError,
    LLMRateLimitError,
    LLMGenerationError,
)
from app.core.logging import get_logger
from app.llm.base import BaseLLMProvider, LLMResponse
from app.llm.factory import register_provider

logger = get_logger(__name__)


@register_provider("groq")
class GroqProvider(BaseLLMProvider):
    """Groq cloud LLM provider.

    Uses the Groq API for ultra-fast inference on open-source models.
    Supports both direct SDK calls (for fine-grained control) and
    LangChain integration (for chain / agent pipelines).

    Attributes:
        _client: Async Groq SDK client.
        _model: The Groq model identifier.
        _temperature: Default sampling temperature.
        _max_tokens: Default maximum tokens for generation.
        _max_retries: Maximum number of retry attempts for transient errors.
        _retry_delay: Base delay (seconds) for exponential backoff.
        _api_key: Groq API key (stored for LangChain client construction).
    """

    def __init__(self, settings: Settings) -> None:
        """Initialize the Groq provider.

        Args:
            settings: Application settings containing Groq configuration.

        Raises:
            LLMConfigurationError: If the Groq API key is missing or empty.
        """
        if not settings.GROQ_API_KEY:
            raise LLMConfigurationError(
                provider="groq",
                message="GROQ_API_KEY is required but not set. "
                "Please set it in your environment or .env file.",
            )

        self._api_key: str = settings.GROQ_API_KEY
        self._model: str = settings.GROQ_MODEL
        self._temperature: float = settings.GROQ_TEMPERATURE
        self._max_tokens: int = settings.GROQ_MAX_TOKENS
        self._max_retries: int = settings.GROQ_MAX_RETRIES
        self._retry_delay: float = settings.GROQ_RETRY_DELAY

        self._client = AsyncGroq(api_key=self._api_key)

        logger.info(
            "groq_provider_initialized",
            model=self._model,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
            max_retries=self._max_retries,
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def provider_name(self) -> str:
        """Return the provider name.

        Returns:
            str: Always ``'groq'``.
        """
        return "groq"

    @property
    def model_name(self) -> str:
        """Return the active Groq model name.

        Returns:
            str: The configured Groq model identifier.
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
        """Generate a single, complete response from the Groq API.

        Builds a message list from the prompt (and optional system prompt),
        sends it to the Groq chat completions endpoint, and returns a
        standardized :class:`LLMResponse`.

        Args:
            prompt: The user prompt to send.
            system_prompt: Optional system instruction.
            temperature: Sampling temperature override.
            max_tokens: Max tokens override.
            **kwargs: Passed directly to the Groq API.

        Returns:
            LLMResponse: Standardized response with content, usage, etc.

        Raises:
            LLMRateLimitError: When Groq rate limits are exceeded.
            LLMConnectionError: When the Groq API is unreachable.
            LLMGenerationError: For any other API error.
        """
        messages = self._build_messages(prompt, system_prompt)
        effective_temperature = temperature if temperature is not None else self._temperature
        effective_max_tokens = max_tokens if max_tokens is not None else self._max_tokens

        try:
            response = await self._generate_with_retry(
                messages=messages,
                temperature=effective_temperature,
                max_tokens=effective_max_tokens,
                **kwargs,
            )
        except RateLimitError as exc:
            logger.warning("groq_rate_limit_exceeded", model=self._model, error=str(exc))
            raise LLMRateLimitError(
                provider="groq",
                message=f"Groq rate limit exceeded: {exc}",
                retry_after=getattr(exc, "retry_after", None),
            ) from exc
        except APIConnectionError as exc:
            logger.error("groq_connection_error", model=self._model, error=str(exc))
            raise LLMConnectionError(
                provider="groq",
                message=f"Failed to connect to Groq API: {exc}",
            ) from exc
        except APIStatusError as exc:
            logger.error(
                "groq_api_status_error",
                model=self._model,
                status_code=exc.status_code,
                error=str(exc),
            )
            raise LLMGenerationError(
                provider="groq",
                message=f"Groq API error (HTTP {exc.status_code}): {exc}",
            ) from exc

        choice = response.choices[0]
        usage = response.usage

        return LLMResponse(
            content=choice.message.content or "",
            model=response.model,
            provider="groq",
            usage={
                "prompt_tokens": usage.prompt_tokens if usage else 0,
                "completion_tokens": usage.completion_tokens if usage else 0,
                "total_tokens": usage.total_tokens if usage else 0,
            },
            finish_reason=choice.finish_reason,
            raw_response=response.model_dump() if hasattr(response, "model_dump") else {},
        )

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response from the Groq API.

        Yields content chunks as they are received from the API.

        Args:
            prompt: The user prompt to send.
            system_prompt: Optional system instruction.
            temperature: Sampling temperature override.
            max_tokens: Max tokens override.
            **kwargs: Passed directly to the Groq API.

        Yields:
            str: Individual text chunks of the generated content.

        Raises:
            LLMRateLimitError: When Groq rate limits are exceeded.
            LLMConnectionError: When the Groq API is unreachable.
            LLMGenerationError: For any other API error.
        """
        messages = self._build_messages(prompt, system_prompt)
        effective_temperature = temperature if temperature is not None else self._temperature
        effective_max_tokens = max_tokens if max_tokens is not None else self._max_tokens

        try:
            stream = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=effective_temperature,
                max_tokens=effective_max_tokens,
                stream=True,
                **kwargs,
            )

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except RateLimitError as exc:
            logger.warning("groq_stream_rate_limit", model=self._model, error=str(exc))
            raise LLMRateLimitError(
                provider="groq",
                message=f"Groq rate limit exceeded during streaming: {exc}",
                retry_after=getattr(exc, "retry_after", None),
            ) from exc
        except APIConnectionError as exc:
            logger.error("groq_stream_connection_error", model=self._model, error=str(exc))
            raise LLMConnectionError(
                provider="groq",
                message=f"Failed to connect to Groq API during streaming: {exc}",
            ) from exc
        except APIStatusError as exc:
            logger.error(
                "groq_stream_api_error",
                model=self._model,
                status_code=exc.status_code,
                error=str(exc),
            )
            raise LLMGenerationError(
                provider="groq",
                message=f"Groq API error during streaming (HTTP {exc.status_code}): {exc}",
            ) from exc

    # ------------------------------------------------------------------
    # LangChain Integration
    # ------------------------------------------------------------------

    def get_langchain_llm(self) -> BaseChatModel:
        """Get a LangChain-compatible ``ChatGroq`` instance.

        Returns a ``ChatGroq`` model configured with the same settings
        as this provider, suitable for use in LangChain chains, LangGraph
        agents, and RAG pipelines.

        Returns:
            BaseChatModel: A configured ``ChatGroq`` instance.
        """
        return ChatGroq(
            api_key=self._api_key,
            model=self._model,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
            max_retries=self._max_retries,
        )

    # ------------------------------------------------------------------
    # Health Check
    # ------------------------------------------------------------------

    async def health_check(self) -> dict:
        """Check Groq API connectivity and measure latency.

        Sends a minimal generation request (``"ping"``, ``max_tokens=5``)
        and records the round-trip time.

        Returns:
            dict: Health status with keys:
                - provider (str): ``'groq'``.
                - model (str): The configured model.
                - status (str): ``'healthy'`` or ``'unhealthy'``.
                - latency_ms (float): Round-trip latency in milliseconds.
                - error (str, optional): Error message if unhealthy.
        """
        start_time = time.monotonic()
        try:
            await self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
                temperature=0.0,
            )
            latency_ms = (time.monotonic() - start_time) * 1000

            logger.debug("groq_health_check_passed", latency_ms=round(latency_ms, 2))
            return {
                "provider": "groq",
                "model": self._model,
                "status": "healthy",
                "latency_ms": round(latency_ms, 2),
            }
        except Exception as exc:
            latency_ms = (time.monotonic() - start_time) * 1000
            logger.warning("groq_health_check_failed", error=str(exc))
            return {
                "provider": "groq",
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
    ) -> list[dict[str, str]]:
        """Build the message list for the Groq chat completions API.

        Args:
            prompt: The user message content.
            system_prompt: Optional system instruction prepended to the
                conversation.

        Returns:
            list[dict[str, str]]: A list of message dicts with 'role' and
                'content' keys, ready for the API call.
        """
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return messages

    @retry(
        retry=retry_if_exception_type(RateLimitError),
        wait=wait_exponential(multiplier=1, min=1, max=60),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def _generate_with_retry(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
        **kwargs,
    ):
        """Execute a Groq chat completion with automatic retry on rate limits.

        Uses tenacity for exponential backoff. The retry count is derived
        from ``_max_retries`` at decoration time (defaults to 3 attempts).

        Args:
            messages: The formatted message list.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens for generation.
            **kwargs: Additional API parameters.

        Returns:
            The raw Groq API response object.

        Raises:
            RateLimitError: Re-raised after all retry attempts are exhausted.
            APIConnectionError: On connection failure (not retried).
            APIStatusError: On non-rate-limit API errors (not retried).
        """
        logger.debug(
            "groq_generate_attempt",
            model=self._model,
            message_count=len(messages),
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
