from datetime import datetime, timezone
from pydantic import Field
from beanie import Document


class RefreshToken(Document):
    user_id: str
    token: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "refresh_tokens"
