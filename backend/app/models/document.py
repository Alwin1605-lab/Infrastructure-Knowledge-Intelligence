"""Document model — Infrastructure document metadata.

Stores metadata about uploaded infrastructure documents: PDF reports,
maintenance manuals, inspection reports, engineering standards, and
research papers. The actual file is stored on disk; this model holds
the metadata, extracted text, and processing status.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from beanie import Document as BeanieDocument
from pydantic import BaseModel, Field


class DocumentStatus(str, Enum):
    """Processing status of an uploaded document."""

    UPLOADED = "uploaded"
    EXTRACTING = "extracting"
    EXTRACTED = "extracted"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXING_KG = "indexing_kg"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentType(str, Enum):
    """Type of infrastructure document."""

    INSPECTION_REPORT = "inspection_report"
    MAINTENANCE_MANUAL = "maintenance_manual"
    ENGINEERING_STANDARD = "engineering_standard"
    RESEARCH_PAPER = "research_paper"
    GENERAL = "general"


class ExtractedPage(BaseModel):
    """Text content and metadata for a single extracted page.

    This is an embedded sub-model, NOT a standalone MongoDB collection.
    """

    page_number: int = Field(..., description="1-indexed page number.")
    text: str = Field(..., description="Extracted text content.")
    sections: list[str] = Field(
        default_factory=list,
        description="Section headings detected on this page.",
    )
    char_count: int = Field(0, description="Number of characters on this page.")


class Document(BeanieDocument):
    """Infrastructure document metadata stored in MongoDB.

    Represents an uploaded document with its metadata, processing status,
    and extracted text content. The file itself is stored on disk.

    Lifecycle:
        uploaded → extracting → extracted → chunking → embedding → indexing_kg → completed

    Attributes:
        filename: Original filename as uploaded.
        file_path: Server-side storage path.
        file_size_bytes: File size in bytes.
        document_type: Category of the document.
        status: Current processing status.
        pages: List of extracted page content with metadata.
        total_pages: Total number of pages in the document.
        total_chunks: Number of chunks created from the document.
        metadata: Additional user-provided or extracted metadata.
        error_message: Error details if processing failed.
        created_at: Upload timestamp.
        updated_at: Last update timestamp.
    """

    filename: str = Field(..., description="Original filename.")
    file_path: str = Field(..., description="Server-side file storage path.")
    file_size_bytes: int = Field(..., description="File size in bytes.")
    content_type: str = Field(
        default="application/pdf",
        description="MIME type of the file.",
    )
    document_type: DocumentType = Field(
        default=DocumentType.GENERAL,
        description="Category of the document.",
    )
    status: DocumentStatus = Field(
        default=DocumentStatus.UPLOADED,
        description="Current processing status.",
    )

    # --- Extracted Content ---
    pages: list[ExtractedPage] = Field(
        default_factory=list,
        description="Extracted page content with metadata.",
    )
    full_text: str = Field(
        default="",
        description="Concatenated full text (for display purposes).",
    )
    total_pages: int = Field(0, description="Total number of pages.")
    total_chunks: int = Field(0, description="Number of chunks generated.")
    total_kg_entities: int = Field(0, description="Number of KG entities extracted.")
    total_kg_relationships: int = Field(0, description="Number of KG relationships extracted.")

    # --- Additional Metadata ---
    metadata: dict = Field(
        default_factory=dict,
        description="Additional metadata (e.g., author, title, date).",
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if processing failed.",
    )

    # --- Timestamps ---
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Upload timestamp (UTC).",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last update timestamp (UTC).",
    )

    class Settings:
        """Beanie collection settings."""

        name = "documents"
        indexes = [
            "filename",
            "status",
            "document_type",
            "created_at",
        ]

    def mark_extracting(self) -> None:
        """Transition to 'extracting' status."""
        self.status = DocumentStatus.EXTRACTING
        self.updated_at = datetime.now(timezone.utc)

    def mark_extracted(self, pages: list[ExtractedPage], full_text: str) -> None:
        """Transition to 'extracted' with page data."""
        self.status = DocumentStatus.EXTRACTED
        self.pages = pages
        self.full_text = full_text
        self.total_pages = len(pages)
        self.updated_at = datetime.now(timezone.utc)

    def mark_completed(self, total_chunks: int) -> None:
        """Transition to 'completed' with chunk count."""
        self.status = DocumentStatus.COMPLETED
        self.total_chunks = total_chunks
        self.updated_at = datetime.now(timezone.utc)

    def mark_kg_indexed(self, entities: int, relationships: int) -> None:
        """Update KG extraction statistics."""
        self.total_kg_entities = entities
        self.total_kg_relationships = relationships
        self.updated_at = datetime.now(timezone.utc)

    def mark_failed(self, error: str) -> None:
        """Transition to 'failed' with error message."""
        self.status = DocumentStatus.FAILED
        self.error_message = error
        self.updated_at = datetime.now(timezone.utc)
