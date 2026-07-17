"""Abstract base class for LLM providers.

All LLM providers must implement this interface. This ensures that
the rest of the application can work with any provider without
knowing provider-specific details.

Design Decisions:
    - Uses dataclass for LLMResponse to keep response handling simple and typed.
    - AsyncGenerator for streaming to allow natural async iteration.
    - get_langchain_llm() bridges our abstraction with the LangChain ecosystem.
    - health_check() enables monitoring and readiness probes.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncGenerator

from langchain_core.language_models import BaseChatModel


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider.

    Attributes:
        content: The generated text content from the LLM.
        model: The model identifier used for generation (e.g., 'llama-3.3-70b-versatile').
        provider: The provider name (e.g., 'groq', 'ollama').
        usage: Token usage statistics with keys: prompt_tokens, completion_tokens, total_tokens.
        finish_reason: Why the model stopped generating (e.g., 'stop', 'length', 'content_filter').
        raw_response: Provider-specific raw response data for debugging or advanced usage.
    """

    content: str
    model: str
    provider: str
    usage: dict = field(default_factory=dict)
    finish_reason: str | None = None
    raw_response: dict = field(default_factory=dict)


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers.

    All LLM providers must implement these methods:
        - generate: Single response generation.
        - generate_stream: Streaming response generation.
        - get_langchain_llm: LangChain-compatible chat model.
        - health_check: Provider connectivity check.

    Example:
        >>> provider = create_llm_provider(settings)
        >>> response = await provider.generate(prompt="Explain OSPF.")
        >>> print(response.content)
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name (e.g., 'groq', 'ollama').

        Returns:
            str: A lowercase identifier for this provider.
        """
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the active model name.

        Returns:
            str: The model identifier currently configured for this provider.
        """
        ...

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs,
    ) -> LLMResponse:
        """Generate a single, complete response from the LLM.

        Args:
            prompt: The user prompt / query to send to the model.
            system_prompt: Optional system-level instruction to guide the model's behavior.
            temperature: Sampling temperature override. Higher values increase randomness.
            max_tokens: Maximum number of tokens to generate. Overrides the default.
            **kwargs: Additional provider-specific parameters.

        Returns:
            LLMResponse: A standardized response object containing the generated content.

        Raises:
            LLMConnectionError: If the provider is unreachable.
            LLMRateLimitError: If the provider rate limit is exceeded.
            LLMGenerationError: If generation fails for any other reason.
        """
        ...

    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response from the LLM.

        Yields content chunks as they become available. Useful for real-time
        display of long-form responses.

        Args:
            prompt: The user prompt / query to send to the model.
            system_prompt: Optional system-level instruction to guide the model's behavior.
            temperature: Sampling temperature override. Higher values increase randomness.
            max_tokens: Maximum number of tokens to generate. Overrides the default.
            **kwargs: Additional provider-specific parameters.

        Yields:
            str: Individual text chunks of the generated content.

        Raises:
            LLMConnectionError: If the provider is unreachable.
            LLMRateLimitError: If the provider rate limit is exceeded.
            LLMGenerationError: If generation fails for any other reason.
        """
        ...

    @abstractmethod
    def get_langchain_llm(self) -> BaseChatModel:
        """Get a LangChain-compatible chat model instance.

        Used by LangChain chains, LangGraph agents, and RAG pipelines
        that need a standardized LLM interface.

        Returns:
            BaseChatModel: A LangChain chat model configured with this provider's settings.
        """
        ...

    @abstractmethod
    async def health_check(self) -> dict:
        """Check provider connectivity and return status information.

        Performs a lightweight request to verify the provider is reachable
        and the configured model is available.

        Returns:
            dict: Status information with keys:
                - provider (str): Provider name.
                - model (str): Model name.
                - status (str): 'healthy' or 'unhealthy'.
                - latency_ms (float): Round-trip latency in milliseconds.
                - error (str, optional): Error message if unhealthy.
        """
        ...
