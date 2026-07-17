"""Neo4j knowledge graph connection management.

Manages the lifecycle of the Neo4j AsyncGraphDatabase driver and sessions
for the Building Knowledge Graph. Also handles initialization of graph constraints
and indexes for building entities.

Usage:
    # During startup:
    await init_kg(settings)

    # During shutdown:
    await close_kg()

    # Anywhere in services:
    driver = get_neo4j_driver()
"""

import asyncio
from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager

import neo4j
from neo4j import AsyncGraphDatabase, AsyncDriver

from app.config import Settings
from app.core.exceptions import KGConnectionError
from app.core.logging import get_logger

logger = get_logger(__name__)

# Module-level references
_driver: Optional[AsyncDriver] = None


async def init_kg(settings: Settings) -> Optional[AsyncDriver]:
    """Initialize the Neo4j async driver and set up building knowledge graph constraints.

    Creates unique constraints and indexes for canonical building entities
    (Defect, Cause, Component, Material, RepairMethod, Risk, Document, Page).

    Args:
        settings: Application settings with Neo4j URI and credentials.

    Returns:
        The Neo4j AsyncDriver instance, or None if connection failed and fallback is used.

    Raises:
        KGConnectionError: If Neo4j connection fails and critical graph mode is required.
    """
    global _driver

    logger.info(
        "neo4j_connecting",
        uri=settings.NEO4J_URI,
        user=settings.NEO4J_USER,
    )

    try:
        auth = (settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        _driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=auth,
            max_connection_lifetime=3600,
            max_connection_pool_size=50,
            connection_acquisition_timeout=10.0,
        )

        # Verify connectivity
        await _driver.verify_connectivity()
        logger.info("neo4j_connected", uri=settings.NEO4J_URI)

        # Initialize constraints and indexes asynchronously
        await _setup_constraints_and_indexes(_driver)
        logger.info("neo4j_constraints_initialized")

        return _driver

    except Exception as exc:
        logger.warning(
            "neo4j_init_failed",
            error=str(exc),
            note="App will start but Knowledge Graph features require Neo4j to be running.",
        )
        if _driver is not None:
            try:
                await _driver.close()
            except Exception:
                pass
        _driver = None
        return None


async def _setup_constraints_and_indexes(driver: AsyncDriver) -> None:
    """Create unique constraints and indexes for building graph nodes."""
    constraints = [
        "CREATE CONSTRAINT defect_name_unique IF NOT EXISTS FOR (n:Defect) REQUIRE n.name IS UNIQUE",
        "CREATE CONSTRAINT cause_name_unique IF NOT EXISTS FOR (n:Cause) REQUIRE n.name IS UNIQUE",
        "CREATE CONSTRAINT component_name_unique IF NOT EXISTS FOR (n:Component) REQUIRE n.name IS UNIQUE",
        "CREATE CONSTRAINT material_name_unique IF NOT EXISTS FOR (n:Material) REQUIRE n.name IS UNIQUE",
        "CREATE CONSTRAINT repair_method_name_unique IF NOT EXISTS FOR (n:RepairMethod) REQUIRE n.name IS UNIQUE",
        "CREATE CONSTRAINT risk_name_unique IF NOT EXISTS FOR (n:Risk) REQUIRE n.name IS UNIQUE",
        "CREATE CONSTRAINT building_standard_name_unique IF NOT EXISTS FOR (n:BuildingStandard) REQUIRE n.name IS UNIQUE",
        "CREATE CONSTRAINT document_id_unique IF NOT EXISTS FOR (n:Document) REQUIRE n.document_id IS UNIQUE",
        "CREATE INDEX page_doc_index IF NOT EXISTS FOR (n:Page) ON (n.document_id, n.page_number)",
    ]

    async with driver.session() as session:
        for cypher in constraints:
            try:
                await session.run(cypher)
            except Exception as exc:
                logger.debug("constraint_setup_notice", cypher=cypher[:40], note=str(exc))


async def close_kg() -> None:
    """Close the Neo4j async driver upon application shutdown."""
    global _driver
    if _driver is not None:
        try:
            await _driver.close()
            logger.info("neo4j_disconnected")
        except AttributeError:
            # Socket pool already closed or cleaned up during asyncio shutdown
            logger.info("neo4j_disconnected")
        except Exception as exc:
            logger.error("neo4j_disconnect_error", error=str(exc))
        finally:
            _driver = None


def get_neo4j_driver() -> AsyncDriver:
    """Get the active Neo4j async driver instance.

    Returns:
        The active Neo4j AsyncDriver.

    Raises:
        KGConnectionError: If Neo4j driver is not initialized or disconnected.
    """
    if _driver is None:
        raise KGConnectionError("Neo4j driver is not initialized or currently disconnected.")
    return _driver


@asynccontextmanager
async def get_neo4j_session(database: str = "neo4j") -> AsyncGenerator[neo4j.AsyncSession, None]:
    """Get an async Neo4j session context manager.

    Args:
        database: Neo4j database name (default: 'neo4j').

    Yields:
        AsyncSession: Active Neo4j session.

    Raises:
        KGConnectionError: If Neo4j driver is not initialized.
    """
    driver = get_neo4j_driver()
    session = driver.session(database=database)
    try:
        yield session
    finally:
        await session.close()
