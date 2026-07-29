"""Report model — Generated infrastructure assessment reports.

Stores metadata and content of generated maintenance/assessment reports
(PDF/DOCX). Links back to the documents and analysis that produced it.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from beanie import Document as BeanieDocument
from pydantic import Field


class ReportFormat(str, Enum):
    """Output format of the generated report."""

    PDF = "pdf"
    DOCX = "docx"


class ReportStatus(str, Enum):
    """Processing status of the report."""

    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class Report(BeanieDocument):
    """Generated infrastructure assessment report stored in MongoDB.

    Attributes:
        title: Report title.
        format: Output format (PDF or DOCX).
        status: Current generation status.
        file_path: Server-side path to the generated file.
        source_document_ids: IDs of documents used to generate this report.
        sections: Report section content (serialized).
        error_message: Error details if generation failed.
        created_at: Generation timestamp (UTC).
    """

    title: str = Field(..., description="Report title.")
    workspace_id: str | None = Field(default=None, description="ID of the workspace this report belongs to.")
    owner_id: str | None = Field(default=None, description="ID of the user who created this report.")
    format: ReportFormat = Field(
        default=ReportFormat.PDF,
        description="Output format.",
    )
    status: ReportStatus = Field(
        default=ReportStatus.GENERATING,
        description="Current generation status.",
    )
    file_path: Optional[str] = Field(
        default=None,
        description="Server-side path to the generated report file.",
    )

    # --- Source Tracking ---
    source_document_ids: list[str] = Field(
        default_factory=list,
        description="IDs of the documents analyzed for this report.",
    )

    # --- Report Content ---
    sections: dict = Field(
        default_factory=dict,
        description="Report sections (executive_summary, defects, causes, recommendations, risks).",
    )

    # --- Error Handling ---
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if generation failed.",
    )

    # --- Timestamps ---
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Creation timestamp (UTC).",
    )

    class Settings:
        """Beanie collection settings."""

        name = "reports"
        indexes = [
            "status",
            "created_at",
            "workspace_id",
            "owner_id"
        ]

    def mark_completed(self, file_path: str) -> None:
        """Mark report as successfully generated."""
        self.status = ReportStatus.COMPLETED
        self.file_path = file_path

    def mark_failed(self, error: str) -> None:
        """Mark report as failed."""
        self.status = ReportStatus.FAILED
        self.error_message = error
