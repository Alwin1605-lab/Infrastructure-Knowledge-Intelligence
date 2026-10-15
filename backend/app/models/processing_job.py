"""ProcessingJob model — tracks background document processing jobs."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from beanie import Document as BeanieDocument
from pydantic import Field


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class JobStep(str, Enum):
    UPLOAD = "upload"
    EXTRACTION = "extraction"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    VECTOR_INDEXING = "vector_indexing"
    KG_EXTRACTION = "kg_extraction"
    KG_INDEXING = "kg_indexing"
    COMPLETED = "completed"


class ProcessingJob(BeanieDocument):
    """Tracks the background processing status of an uploaded document."""
    
    document_id: str = Field(...)
    filename: str = Field(...)
    status: JobStatus = Field(default=JobStatus.QUEUED)
    current_step: JobStep = Field(default=JobStep.UPLOAD)
    completed_steps: list[str] = Field(default_factory=list)
    failed_step: Optional[str] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
    
    # Progress metrics
    total_pages: int = Field(default=0)
    pages_processed: int = Field(default=0)
    pages_extracted: int = Field(default=0)
    chunks_created: int = Field(default=0)
    embeddings_created: int = Field(default=0)
    kg_nodes_created: int = Field(default=0)
    kg_relations_created: int = Field(default=0)
    
    # Timing
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    elapsed_seconds: float = Field(default=0.0)
    
    # Metadata
    user_id: str = Field(...)
    workspace_id: Optional[str] = Field(default=None)
    retry_count: int = Field(default=0)
    failure_stage: Optional[str] = Field(default=None)
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Settings:
        name = "processing_jobs"
        indexes = ["document_id", "status", "user_id", "created_at"]
