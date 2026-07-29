from datetime import datetime, timezone
from pydantic import Field
from beanie import Document


class Organization(Document):
    name: str
    subscription_tier: str = "free"
    owner_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "organizations"
