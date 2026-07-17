"""Structured logging configuration using structlog.

Provides consistent, structured logging throughout the application.
JSON output in production, colored console output in development.

Usage:
    from app.core.logging import setup_logging, get_logger

    # During application startup
    setup_logging(debug=True)

    # In any module
    logger = get_logger(__name__)
    logger.info("Processing document", document_id="abc123", pages=42)
"""

import logging
import sys
from typing import Any

import structlog


def setup_logging(debug: bool = True, json_output: bool = False) -> None:
    """Configure structured logging for the application.

    Sets up structlog with appropriate processors and formatters.
    Should be called once during application startup.

    Args:
        debug: Enable debug-level logging. When False, uses INFO level.
        json_output: Use JSON formatting (recommended for production).
                     When False, uses colored console output for readability.
    """
    log_level = logging.DEBUG if debug else logging.INFO

    # Shared processors applied to all log entries
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if json_output:
        # Production: machine-readable JSON output
        renderer = structlog.processors.JSONRenderer()
    else:
        # Development: human-readable colored console output
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    # Configure structlog's own processing pipeline
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Bridge standard library logging through structlog's formatter
    # so that third-party libraries also produce structured output
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # Reset the root logger and attach our handler
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    # Suppress noisy third-party loggers that flood the console
    for noisy_logger in ["httpx", "httpcore", "chromadb", "neo4j"]:
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance.

    Creates a logger bound with the given name. Use ``__name__``
    as the argument to automatically capture the module path.

    Args:
        name: Logger name (typically ``__name__`` of the calling module).

    Returns:
        A structured logger bound with the given name.

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Server started", port=8000)
    """
    return structlog.get_logger(name)
