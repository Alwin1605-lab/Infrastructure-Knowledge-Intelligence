"""Shared typed state and execution trace for the Agentic Pipeline.

AgentState is passed through every LangGraph node. Each agent reads from it
and writes its own output fields back into it. The pipeline is fully stateless —
one AgentState instance is created per query and discarded after the response.

AgentExecutionStep records per-agent diagnostics:
    - status: success | skipped | failed
    - time_ms: wall-clock execution time
    - confidence: agent-specific confidence score (0.0–1.0)
    - reason: human-readable explanation of the agent's decision
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal, Optional, TYPE_CHECKING

from typing_extensions import TypedDict

if TYPE_CHECKING:
    from app.schemas.chat import ChatResponse, EngineeringRecommendation


# ---------------------------------------------------------------------------
# Per-agent execution step (returned in the final response trace)
# ---------------------------------------------------------------------------


@dataclass
class AgentExecutionStep:
    """Diagnostic record for a single agent's execution.

    Attributes:
        agent: Name of the agent (e.g., "QueryAnalysisAgent").
        status: Execution outcome — "success", "skipped", or "failed".
        time_ms: Wall-clock execution time in milliseconds.
        confidence: Agent-specific confidence score (0.0 = no confidence, 1.0 = certain).
        reason: Human-readable explanation of what the agent decided and why.
        error: Error message if status is "failed".
    """

    agent: str
    status: Literal["success", "skipped", "failed"]
    time_ms: float
    confidence: float
    reason: str
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe dictionary."""
        d = {
            "agent": self.agent,
            "status": self.status,
            "time_ms": round(self.time_ms, 1),
            "confidence": round(self.confidence, 3),
            "reason": self.reason,
        }
        if self.error:
            d["error"] = self.error
        return d


# ---------------------------------------------------------------------------
# Shared LangGraph state (TypedDict for StateGraph compatibility)
# ---------------------------------------------------------------------------


class AgentState(TypedDict, total=False):
    """Mutable state shared across all agent nodes in the LangGraph pipeline.

    All fields are Optional — agents only populate what they produce.
    Downstream agents read what upstream agents wrote.

    Stateless design: one AgentState is created per query, discarded after response.
    """

    # --- Input ---
    session_id: str                   # Unique ID for this execution trace
    original_question: str            # Raw user question
    top_k: int                        # Number of chunks to retrieve
    include_kg: bool                  # Whether to run KG reasoning

    # --- QueryAnalysisAgent output ---
    is_building_domain: bool          # Domain validation result
    rejection_reason: Optional[str]   # Populated if domain is invalid
    query_intent: str                 # e.g., "defect_diagnosis", "maintenance_planning"
    extracted_defects: list[str]
    extracted_components: list[str]
    extracted_repair_methods: list[str]
    reformulated_query: str           # Improved query for retrieval

    # --- RetrievalAgent output ---
    rag_response: Optional[Any]       # ChatResponse from HybridRAGPipeline

    # --- KGReasoningAgent output ---
    enriched_kg_context: str          # Expanded multi-hop KG context text
    risk_chains: list[dict[str, Any]] # Defect → Risk → Component chains

    # --- RecommendationAgent output ---
    structured_recommendations: list[Any]  # List of EngineeringRecommendation
    recommendation_rationale: str          # LLM narrative for recommendations

    # --- ReportAgent output ---
    report_text: str                  # Full structured engineering report

    # --- Execution trace (appended by each agent) ---
    execution_trace: list[AgentExecutionStep]

    # --- Final assembly ---
    pipeline_error: Optional[str]     # Set if orchestrator encounters fatal error


def new_agent_state(
    question: str,
    top_k: int = 5,
    include_kg: bool = True,
) -> AgentState:
    """Create a fresh AgentState for a new stateless query.

    Args:
        question: The raw user question.
        top_k: Number of RAG chunks to retrieve.
        include_kg: Whether to run KG reasoning agent.

    Returns:
        Initialized AgentState with all list fields populated as empty collections.
    """
    return AgentState(
        session_id=str(uuid.uuid4()),
        original_question=question,
        top_k=top_k,
        include_kg=include_kg,
        is_building_domain=True,
        rejection_reason=None,
        query_intent="general",
        extracted_defects=[],
        extracted_components=[],
        extracted_repair_methods=[],
        reformulated_query=question,
        rag_response=None,
        enriched_kg_context="",
        risk_chains=[],
        structured_recommendations=[],
        recommendation_rationale="",
        report_text="",
        execution_trace=[],
        pipeline_error=None,
    )


# ---------------------------------------------------------------------------
# Timer utility used by all agents
# ---------------------------------------------------------------------------


class AgentTimer:
    """Context-free nanosecond timer for measuring agent execution time."""

    def __init__(self) -> None:
        self._start_ns: int = 0

    def start(self) -> None:
        """Record start time."""
        self._start_ns = time.perf_counter_ns()

    def elapsed_ms(self) -> float:
        """Return elapsed time in milliseconds since start()."""
        return (time.perf_counter_ns() - self._start_ns) / 1_000_000
