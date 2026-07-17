"""Shared test fixtures and configuration.

Provides reusable pytest fixtures for the test suite including:
- Test-safe application settings with isolated database names
- Mock LLM provider for unit tests without external API calls
- Async event loop configuration for async test support

Usage::

    def test_something(test_settings, mock_llm_provider):
        assert test_settings.APP_ENV == "testing"
        assert mock_llm_provider.provider_name == "mock"
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from app.config import Settings
from app.llm.base import BaseLLMProvider, LLMResponse


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings with safe defaults.

    Returns a Settings instance configured for testing with:
    - APP_ENV set to "testing"
    - DEBUG enabled
    - Fake API keys (no real external calls)
    - Isolated test database name
    - Local service URIs

    Returns:
        Settings: A test-safe configuration instance.
    """
    return Settings(
        APP_ENV="testing",
        DEBUG=True,
        LLM_PROVIDER="groq",
        GROQ_API_KEY="test_key_not_real",
        GROQ_MODEL="llama-3.1-8b-instant",
        MONGODB_URI="mongodb://localhost:27017",
        MONGODB_DATABASE="infra_knowledge_test",
        NEO4J_URI="bolt://localhost:7687",
        NEO4J_USER="neo4j",
        NEO4J_PASSWORD="test_password",
        CHROMADB_HOST="localhost",
        CHROMADB_PORT=8000,
        UPLOAD_DIR="./test_uploads",
    )


@pytest.fixture
def mock_llm_provider() -> BaseLLMProvider:
    """Create a mock LLM provider for testing.

    Returns an AsyncMock that conforms to the BaseLLMProvider interface,
    pre-configured with sensible default return values for the
    ``generate`` method.

    Returns:
        BaseLLMProvider: A mock LLM provider with preset responses.
    """
    provider = AsyncMock(spec=BaseLLMProvider)
    provider.provider_name = "mock"
    provider.model_name = "mock-model"
    provider.generate.return_value = LLMResponse(
        content="Mock LLM response",
        model="mock-model",
        provider="mock",
        usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
    )
    return provider


@pytest.fixture
def event_loop():
    """Create event loop for async tests.

    Provides a fresh asyncio event loop for each test that requires
    async execution. The loop is properly closed after the test completes.

    Yields:
        asyncio.AbstractEventLoop: A new event loop instance.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
