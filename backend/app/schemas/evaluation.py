"""Pydantic schemas for the Evaluation Framework (Phase 7)."""

from typing import Any, Optional
from pydantic import BaseModel, Field


class BenchmarkRequest(BaseModel):
    category: Optional[str] = Field(
        None, description="Optional category to filter questions (e.g. 'defects', 'materials')."
    )
    top_k: int = Field(5, description="Number of document chunks to retrieve per query.")


class BenchmarkResponse(BaseModel):
    summary: dict[str, Any] = Field(..., description="Overall metrics summary.")
    failure_breakdown: dict[str, int] = Field(..., description="Counts of failures by category.")
    markdown_report_path: Optional[str] = Field(None, description="Path to the saved Markdown report.")
    json_report_path: Optional[str] = Field(None, description="Path to the saved JSON payload.")
    timestamp: float = Field(..., description="Unix timestamp of the benchmark run.")


class AblationRequest(BaseModel):
    question: str = Field(..., description="Question to run through the 5 architectural configurations.")
    top_k: int = Field(5, description="Number of chunks for retrieval.")


class AblationResponse(BaseModel):
    question: str
    ablation_results: dict[str, Any] = Field(
        ...,
        description="Results from llm_only, rag_only, rag_kg, and agentic_ai configurations."
    )
    timestamp: float


class EvaluationHistoryItem(BaseModel):
    filename: str
    date: Optional[str]
    accuracy_percent: Optional[float]
    questions_tested: Optional[int]
    avg_latency_s: Optional[float]


class ExplainabilityResponse(BaseModel):
    session_id: str
    markdown_report: str
    visualization_payload: dict[str, Any]
