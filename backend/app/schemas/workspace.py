from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class WorkspaceCreate(BaseModel):
    name: str
    building_type: Optional[str] = "Unspecified"
    location: Optional[str] = None
    description: Optional[str] = None


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    building_type: str
    location: Optional[str]
    description: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime


class WorkspaceListResponse(BaseModel):
    workspaces: list[WorkspaceResponse]
    total: int
    skip: int
    limit: int
