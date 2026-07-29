from datetime import datetime, timezone
from pydantic import Field
from beanie import Document


class ActivityLog(Document):
    user_id: str
    organization_id: str
    workspace_id: str | None = None
    
    action: str
    details: str | None = None
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "activity_logs"
