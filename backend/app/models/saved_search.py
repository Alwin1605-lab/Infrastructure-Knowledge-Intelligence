"""SavedSearch model — allows users to save frequent searches."""

from datetime import datetime, timezone
from typing import Optional
from beanie import Document as BeanieDocument
from pydantic import Field


class SavedSearch(BeanieDocument):
    """A saved search query for quick re-use."""
    
    user_id: str = Field(...)
    name: str = Field(...)  # User-given label
    query: str = Field(...)  # The search string
    filters: dict = Field(default_factory=dict)  # document_type, workspace_id, etc.
    use_count: int = Field(default=0)
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_used_at: Optional[datetime] = Field(default=None)
    
    class Settings:
        name = "saved_searches"
        indexes = ["user_id", "created_at"]
