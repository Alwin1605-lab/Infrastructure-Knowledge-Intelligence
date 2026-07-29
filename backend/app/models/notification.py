from datetime import datetime, timezone
from pydantic import Field
from beanie import Document


class Notification(Document):
    user_id: str
    title: str
    message: str
    is_read: bool = False
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "notifications"
