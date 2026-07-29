"""Chat history model — Stores conversation history with structured responses.

Each chat entry stores the user's question, the full structured AI response
(all 7 fields), and metadata about the session.
"""

from datetime import datetime, timezone
from typing import Optional

from beanie import Document as BeanieDocument
from pydantic import Field


class ChatHistory(BeanieDocument):
    """Chat conversation entry stored in MongoDB.

    Stores a single question-response pair with the full 7-field
    structured response for audit, research evaluation, and UI display.

    Attributes:
        question: The user's original question.
        answer: The AI-generated answer text.
        sources: Serialized source document citations.
        kg_context: Serialized knowledge graph entity context.
        confidence: Serialized confidence assessment.
        recommendations: Serialized engineering recommendations.
        related_components: Serialized related infrastructure components.
        response_time: Serialized timing breakdown.
        session_id: Optional session identifier for grouping conversations.
        created_at: When this entry was created (UTC).
    """

    workspace_id: str | None = Field(default=None, description="Workspace this conversation belongs to.")
    user_id: str | None = Field(default=None, description="User who initiated this conversation.")
    question: str = Field(..., description="User's original question.")
    answer: str = Field(..., description="AI-generated answer.")

    # Store the structured response sub-fields as dicts for flexibility
    sources: list[dict] = Field(
        default_factory=list,
        description="Source document citations (serialized SourceDocument).",
    )
    kg_context: list[dict] = Field(
        default_factory=list,
        description="Knowledge graph entity context (serialized KGEntityContext).",
    )
    confidence: dict = Field(
        default_factory=dict,
        description="Confidence assessment (serialized ConfidenceScore).",
    )
    recommendations: list[dict] = Field(
        default_factory=list,
        description="Engineering recommendations (serialized).",
    )
    related_components: list[dict] = Field(
        default_factory=list,
        description="Related infrastructure components (serialized).",
    )
    response_time: dict = Field(
        default_factory=dict,
        description="Response timing breakdown (serialized ResponseTime).",
    )

    # --- Session Management ---
    session_id: Optional[str] = Field(
        default=None,
        description="Session ID for grouping related conversations.",
    )

    # --- Timestamps ---
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Entry creation timestamp (UTC).",
    )

    class Settings:
        """Beanie collection settings."""

        name = "chat_history"
        indexes = [
            "session_id",
            "created_at",
            "workspace_id",
            "user_id"
        ]
