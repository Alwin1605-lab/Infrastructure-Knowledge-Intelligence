"""Business logic services.

Each service encapsulates a specific domain concern and is injected
into API route handlers via FastAPI's dependency injection system.
"""

from app.services.document_service import DocumentService

__all__ = ["DocumentService"]
