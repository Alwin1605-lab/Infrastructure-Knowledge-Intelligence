"""Data access repositories for MongoDB collections.

Provides CRUD operations through the repository pattern.

Usage:
    from app.db.repositories import DocumentRepository

    repo = DocumentRepository()
    doc = await repo.get_by_id(doc_id)
"""

from app.db.repositories.document_repo import DocumentRepository
from app.db.repositories.report_repo import ReportRepository

__all__ = ["DocumentRepository", "ReportRepository"]
