from datetime import datetime, timezone
from pydantic import Field
from beanie import Document


class Workspace(Document):
    organization_id: str
    owner_id: str
    name: str
    building_type: str = "Unspecified"
    location: str | None = None
    description: str | None = None
    status: str = "Active"
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "workspaces"
