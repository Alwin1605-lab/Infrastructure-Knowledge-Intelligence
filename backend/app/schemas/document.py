"""Pydantic schemas for document upload and management API endpoints.

Defines request/response schemas for:
    - Document upload responses
    - Document listing and detail views
    - Document status tracking
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.document import DocumentStatus, DocumentType


class DocumentUploadResponse(BaseModel):
    """Response after successfully uploading a document."""

    id: str = Field(..., description="Document ID in MongoDB.")
    filename: str = Field(..., description="Original filename.")
    file_size_bytes: int = Field(..., description="File size in bytes.")
    document_type: DocumentType = Field(..., description="Document category.")
    status: DocumentStatus = Field(..., description="Current processing status.")
    message: str = Field(
        default="Document uploaded successfully.",
        description="Status message.",
    )
    created_at: datetime = Field(..., description="Upload timestamp.")


class DocumentSummary(BaseModel):
    """Summary view of a document (for list endpoints)."""

    id: str = Field(..., description="Document ID.")
    filename: str = Field(..., description="Original filename.")
    document_type: DocumentType = Field(..., description="Document category.")
    status: DocumentStatus = Field(..., description="Processing status.")
    total_pages: int = Field(0, description="Total pages extracted.")
    total_chunks: int = Field(0, description="Number of chunks generated.")
    file_size_bytes: int = Field(0, description="File size in bytes.")
    created_at: datetime = Field(..., description="Upload timestamp.")
    updated_at: datetime = Field(..., description="Last update timestamp.")


class DocumentDetail(DocumentSummary):
    """Detailed view of a document (includes extracted text)."""

    pages: list[dict] = Field(
        default_factory=list,
        description="Extracted page content with metadata.",
    )
    metadata: dict = Field(
        default_factory=dict,
        description="Document metadata (title, author, etc.).",
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if processing failed.",
    )


class DocumentListResponse(BaseModel):
    """Paginated list of documents."""

    documents: list[DocumentSummary] = Field(..., description="List of documents.")
    total: int = Field(..., description="Total number of documents.")
    skip: int = Field(0, description="Pagination offset.")
    limit: int = Field(50, description="Page size.")
