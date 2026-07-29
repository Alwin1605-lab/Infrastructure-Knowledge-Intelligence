from datetime import datetime, timezone
from pydantic import Field
from beanie import Document


class WorkspaceDocument(Document):
    workspace_id: str
    owner_id: str
    filename: str
    content_type: str = "application/pdf"
    file_path: str
    status: str = "uploaded"  # uploaded, indexed, failed
    
    pages: int = 0
    entities_extracted: int = 0
    chunks_created: int = 0
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "workspace_documents"
