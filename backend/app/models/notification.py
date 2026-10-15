"""Notification model."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from beanie import Document as BeanieDocument
from pydantic import Field


class NotificationType(str, Enum):
    DOCUMENT_INDEXED = "document_indexed"
    EMBEDDING_COMPLETE = "embedding_complete"
    KG_UPDATED = "kg_updated"
    REPORT_READY = "report_ready"
    REINDEX_COMPLETE = "reindex_complete"
    JOB_FAILED = "job_failed"
    DUPLICATE_DETECTED = "duplicate_detected"
    SYSTEM = "system"


class Notification(BeanieDocument):
    """User notification."""
    
    user_id: str = Field(...)
    title: str = Field(...)
    message: str = Field(...)
    notification_type: NotificationType = Field(default=NotificationType.SYSTEM)
    is_read: bool = Field(default=False)
    link: Optional[str] = Field(default=None)  # e.g. /docs?id=...
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    read_at: Optional[datetime] = Field(default=None)
    
    class Settings:
        name = "notifications"
        indexes = ["user_id", "is_read", "created_at"]
