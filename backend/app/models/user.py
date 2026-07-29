from datetime import datetime, timezone
from pydantic import EmailStr, Field
from beanie import Document, Indexed


class User(Document):
    email: Indexed(EmailStr, unique=True)
    full_name: str
    hashed_password: str
    organization_id: str
    role: str = "Engineer"
    avatar: str | None = None
    is_active: bool = True
    is_guest: bool = False
    
    last_login: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "users"
