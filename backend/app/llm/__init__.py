"""LLM Provider Abstraction Layer.

This module provides a provider-agnostic interface for LLM interactions.
No other module in the application should import provider-specific SDKs directly.

Usage:
    from app.llm import create_llm_provider, BaseLLMProvider

    provider = create_llm_provider(settings)
    response = await provider.generate(prompt="...")
"""

from app.llm.base import BaseLLMProvider, LLMResponse
from app.llm.factory import create_llm_provider

__all__ = ["BaseLLMProvider", "LLMResponse", "create_llm_provider"]
