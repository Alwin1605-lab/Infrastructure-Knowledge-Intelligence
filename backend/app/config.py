"""Centralized application configuration.

All settings are loaded from environment variables via Pydantic Settings.
Never hardcode configuration values - always use this module.

Usage:
    from app.config import get_settings

    settings = get_settings()
    print(settings.APP_NAME)
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Each field maps to an environment variable of the same name.
    Default values are provided for local development.
    In production, set these via .env file or system environment.
    """

    # --- Application ---
    APP_NAME: str = "BuildingKnowledgeIntelligence"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # --- LLM Provider ---
    LLM_PROVIDER: str = "groq"  # Options: groq | ollama

    # --- Groq ---
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.1-8b-instant"
    GROQ_MAX_RETRIES: int = 3
    GROQ_RETRY_DELAY: float = 1.0
    GROQ_TEMPERATURE: float = 0.1
    GROQ_MAX_TOKENS: int = 4096

    # --- Ollama ---
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"

    # --- Embedding ---
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DEVICE: str = "cpu"  # Options: cpu | cuda

    # --- MongoDB ---
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DATABASE: str = "building_knowledge"

    # --- Neo4j ---
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"

    # --- ChromaDB ---
    CHROMADB_HOST: str = "localhost"
    CHROMADB_PORT: int = 8000
    CHROMADB_COLLECTION: str = "building_documents"

    # --- RAG ---
    RAG_TOP_K: int = 5
    RAG_SIMILARITY_THRESHOLD: float = 0.7
    RAG_CHUNK_SIZE: int = 1000
    RAG_CHUNK_OVERLAP: int = 200

    # --- File Storage ---
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 50

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    @model_validator(mode="after")
    def validate_provider_keys(self) -> 'Settings':
        """Ensure necessary API keys are present for the chosen provider."""
        if self.LLM_PROVIDER == "groq" and not self.GROQ_API_KEY:
            # We don't raise an error strictly to allow local fallback/tests, 
            # but in production, we should log a warning or enforce it.
            if self.APP_ENV == "production":
                raise ValueError("GROQ_API_KEY must be set in production when using groq provider")
        return self


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance.

    Uses lru_cache to ensure settings are loaded only once
    during the application lifecycle. This avoids reading the
    .env file on every access.

    To create a fresh instance in tests:
        settings = Settings.model_validate({})
    """
    return Settings()
