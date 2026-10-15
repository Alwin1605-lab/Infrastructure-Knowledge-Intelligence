from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List
from beanie import Document
from pydantic import Field

class AcquisitionStatus(str, Enum):
    METADATA_REVIEW = "metadata_review"
    DOWNLOADING = "downloading"
    FULL_REVIEW = "full_review"
    INDEXED = "indexed"
    REJECTED = "rejected"
    ERROR = "error"

class SourceRegistry(Document):
    name: str
    base_url: str
    source_type: str # "government", "research", "manufacturer"
    connector_type: str # e.g. "openalex", "web"
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    class Settings:
        name = "source_registry"

class AcquiredDocument(Document):
    title: str
    authors: List[str] = Field(default_factory=list)
    year: Optional[int] = None
    doi: Optional[str] = None
    source_url: str
    pdf_url: Optional[str] = None
    local_file_path: Optional[str] = None
    
    status: AcquisitionStatus = Field(default=AcquisitionStatus.METADATA_REVIEW)
    error_message: Optional[str] = None
    
    # Classification & Assessment (populated after download)
    category_assigned: Optional[str] = None
    relevance_score: float = 0.0
    value_score: float = 0.0
    rag_suitability: float = 0.0
    kg_suitability: float = 0.0
    quality_summary: Optional[str] = None
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    class Settings:
        name = "acquired_documents"

class AcquisitionTask(Document):
    query: str
    connector: str
    status: str = "running"
    docs_found: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    class Settings:
        name = "acquisition_tasks"
