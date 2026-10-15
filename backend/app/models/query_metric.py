"""QueryMetric model — tracks performance of each AI query."""

from datetime import datetime, timezone
from typing import Optional
from beanie import Document as BeanieDocument
from pydantic import Field


class QueryMetric(BeanieDocument):
    """Stores performance metrics for each query through the AI pipeline."""
    
    question: str = Field(...)
    user_id: str = Field(...)
    workspace_id: Optional[str] = Field(default=None)
    
    # Timing in milliseconds
    embedding_time_ms: float = Field(default=0.0)
    retrieval_time_ms: float = Field(default=0.0)
    llm_time_ms: float = Field(default=0.0)
    total_time_ms: float = Field(default=0.0)
    
    # Results
    documents_retrieved: int = Field(default=0)
    chunks_retrieved: int = Field(default=0)
    confidence_score: float = Field(default=0.0)
    
    # Pipeline
    pipeline_type: str = Field(default="rag")  # "rag" or "agent"
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Settings:
        name = "query_metrics"
        indexes = ["user_id", "created_at", "pipeline_type"]
