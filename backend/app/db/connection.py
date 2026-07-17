"""MongoDB connection management using Motor + Beanie.

Handles async connection lifecycle: initialization with Beanie ODM
document model registration, and graceful shutdown.

Usage:
    # During startup (in main.py lifespan):
    await init_db(settings)

    # During shutdown:
    await close_db()
"""

from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

from app.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Module-level client reference for cleanup
_client: AsyncIOMotorClient | None = None


async def init_db(settings: Settings) -> AsyncIOMotorClient:
    """Initialize MongoDB connection and Beanie ODM.

    Creates an async Motor client, selects the configured database,
    and initializes Beanie with all document models.

    Args:
        settings: Application settings with MongoDB URI and database name.

    Returns:
        The Motor async client instance.

    Raises:
        ConnectionError: If MongoDB is unreachable.
    """
    global _client

    logger.info(
        "mongodb_connecting",
        uri=settings.MONGODB_URI,
        database=settings.MONGODB_DATABASE,
    )

    _client = AsyncIOMotorClient(
        settings.MONGODB_URI,
        serverSelectionTimeoutMS=5000,
    )

    # Import all Beanie document models
    from app.models import ALL_MODELS

    await init_beanie(
        database=_client[settings.MONGODB_DATABASE],
        document_models=ALL_MODELS,
    )

    logger.info(
        "mongodb_connected",
        database=settings.MONGODB_DATABASE,
        models=len(ALL_MODELS),
    )

    return _client


async def close_db() -> None:
    """Close the MongoDB connection gracefully.

    Should be called during application shutdown to release resources.
    """
    global _client

    if _client is not None:
        _client.close()
        _client = None
        logger.info("mongodb_disconnected")


async def get_client() -> AsyncIOMotorClient:
    """Get the active Motor client.

    Returns:
        The Motor async client instance.

    Raises:
        RuntimeError: If the database has not been initialized.
    """
    if _client is None:
        raise RuntimeError(
            "MongoDB client is not initialized. Call init_db() first."
        )
    return _client
