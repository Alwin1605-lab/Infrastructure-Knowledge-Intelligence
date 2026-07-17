"""LLM Provider Factory.

Reads LLM_PROVIDER from configuration and instantiates the correct provider.
This is the ONLY place in the application where provider selection happens.

Design Decisions:
    - Uses a registry pattern with decorator-based registration so new
      providers can be added without modifying this file.
    - Lazy imports of provider modules to avoid loading unused SDKs and
      to populate the registry on demand.
"""

from app.config import Settings
from app.core.exceptions import UnsupportedProviderError
from app.core.logging import get_logger
from app.llm.base import BaseLLMProvider

logger = get_logger(__name__)

# Registry of supported providers, populated by @register_provider decorators.
_PROVIDER_REGISTRY: dict[str, type[BaseLLMProvider]] = {}


def register_provider(name: str):
    """Decorator to register an LLM provider class in the factory registry.

    This decorator is applied to concrete provider classes so the factory
    can discover and instantiate them by name.

    Args:
        name: The provider identifier (e.g., 'groq', 'ollama'). Must be
              lowercase and match the value used in LLM_PROVIDER config.

    Returns:
        A class decorator that registers the provider class.

    Example:
        >>> @register_provider("groq")
        ... class GroqProvider(BaseLLMProvider):
        ...     ...
    """

    def decorator(cls: type[BaseLLMProvider]) -> type[BaseLLMProvider]:
        _PROVIDER_REGISTRY[name] = cls
        logger.debug("llm_provider_registered", provider=name, cls=cls.__name__)
        return cls

    return decorator


def create_llm_provider(settings: Settings) -> BaseLLMProvider:
    """Create an LLM provider instance based on application configuration.

    Reads the ``LLM_PROVIDER`` field from *settings* and looks up the
    corresponding provider class in the internal registry.  Provider
    modules are imported lazily so that only the required SDK is loaded.

    Args:
        settings: Application settings containing LLM configuration
                  (provider name, API keys, model names, etc.).

    Returns:
        BaseLLMProvider: An initialized, ready-to-use LLM provider instance.

    Raises:
        UnsupportedProviderError: If the configured provider name does not
            match any registered provider.

    Example:
        >>> from app.config import get_settings
        >>> settings = get_settings()
        >>> provider = create_llm_provider(settings)
        >>> print(provider.provider_name)
        'groq'
    """
    # Lazy imports to populate the registry only when needed.
    # This avoids importing heavy SDKs (groq, langchain-ollama) at module load time.
    from app.llm import groq_provider  # noqa: F401
    from app.llm import ollama_provider  # noqa: F401

    provider_name = settings.LLM_PROVIDER.lower()

    if provider_name not in _PROVIDER_REGISTRY:
        raise UnsupportedProviderError(
            provider=provider_name,
            supported=list(_PROVIDER_REGISTRY.keys()),
        )

    provider_cls = _PROVIDER_REGISTRY[provider_name]
    provider = provider_cls(settings)

    logger.info(
        "llm_provider_created",
        provider=provider.provider_name,
        model=provider.model_name,
    )

    return provider
