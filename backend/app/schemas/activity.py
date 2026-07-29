from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ActivityResponse(BaseModel):
    id: str
    user_id: str
    workspace_id: Optional[str]
    action: str
    details: Optional[str]
    timestamp: datetime


class ActivityListResponse(BaseModel):
    activities: list[ActivityResponse]
    total: int
