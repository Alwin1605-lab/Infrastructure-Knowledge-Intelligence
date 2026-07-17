"""Document repository — CRUD operations for infrastructure documents.

Provides async data access for the Document collection in MongoDB
using Beanie ODM. Follows the repository pattern to keep data access
logic separate from business logic.
"""

from typing import Optional

from beanie import PydanticObjectId

from app.core.exceptions import DocumentNotFoundError
from app.core.logging import get_logger
from app.models.document import Document, DocumentStatus

logger = get_logger(__name__)


class DocumentRepository:
    """Repository for Document CRUD operations.

    All methods are static/class methods since Beanie models
    provide built-in query capabilities.
    """

    @staticmethod
    async def create(document: Document) -> Document:
        """Insert a new document into MongoDB.

        Args:
            document: The Document model instance to persist.

        Returns:
            The persisted Document with its generated _id.
        """
        await document.insert()
        logger.info("document_created", document_id=str(document.id), filename=document.filename)
        return document

    @staticmethod
    async def get_by_id(document_id: str) -> Document:
        """Retrieve a document by its ID.

        Args:
            document_id: The MongoDB ObjectId as a string.

        Returns:
            The matching Document.

        Raises:
            DocumentNotFoundError: If no document with the given ID exists.
        """
        doc = await Document.get(PydanticObjectId(document_id))
        if doc is None:
            raise DocumentNotFoundError(document_id)
        return doc

    @staticmethod
    async def get_all(
        skip: int = 0,
        limit: int = 50,
        status: Optional[DocumentStatus] = None,
    ) -> list[Document]:
        """Retrieve all documents with optional filtering.

        Args:
            skip: Number of documents to skip (pagination offset).
            limit: Maximum number of documents to return.
            status: Optional status filter.

        Returns:
            List of matching Documents, ordered by creation date (newest first).
        """
        query = Document.find()
        if status is not None:
            query = Document.find(Document.status == status)

        return await query.sort(-Document.created_at).skip(skip).limit(limit).to_list()

    @staticmethod
    async def update(document: Document) -> Document:
        """Update an existing document.

        Args:
            document: The Document model instance with updated fields.

        Returns:
            The updated Document.
        """
        await document.save()
        logger.debug("document_updated", document_id=str(document.id), status=document.status)
        return document

    @staticmethod
    async def delete(document_id: str) -> bool:
        """Delete a document by its ID.

        Args:
            document_id: The MongoDB ObjectId as a string.

        Returns:
            True if the document was deleted.

        Raises:
            DocumentNotFoundError: If no document with the given ID exists.
        """
        doc = await Document.get(PydanticObjectId(document_id))
        if doc is None:
            raise DocumentNotFoundError(document_id)
        await doc.delete()
        logger.info("document_deleted", document_id=document_id)
        return True

    @staticmethod
    async def count(status: Optional[DocumentStatus] = None) -> int:
        """Count documents with optional status filter.

        Args:
            status: Optional status filter.

        Returns:
            Number of matching documents.
        """
        if status is not None:
            return await Document.find(Document.status == status).count()
        return await Document.find().count()

    @staticmethod
    async def get_by_status(status: DocumentStatus) -> list[Document]:
        """Retrieve all documents with a specific status.

        Args:
            status: The document status to filter by.

        Returns:
            List of Documents with the given status.
        """
        return await Document.find(
            Document.status == status
        ).sort(-Document.created_at).to_list()
