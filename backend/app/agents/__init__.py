"""Phase 6 — Agentic AI Module.

Multi-agent orchestration for the Building Knowledge Intelligence System.
Built with LangGraph StateGraph, each agent has a single responsibility.

Agent Pipeline:
    QueryAnalysisAgent → RetrievalAgent → KGReasoningAgent
        → RecommendationAgent → ReportAgent

Each agent records:
    - status (success | skipped | failed)
    - time_ms (execution duration)
    - confidence (0.0–1.0, agent-specific)
    - reason (human-readable explanation of what the agent decided)

Domain: Buildings Only (RCC, Residential, Commercial, Institutional, Government).
Stateless: Each query is processed independently with no session memory.
"""

from app.agents.orchestrator import AgentOrchestrator
from app.agents.state import AgentState, AgentExecutionStep
from app.agents.base import BaseAgent

__all__ = [
    "AgentOrchestrator",
    "AgentState",
    "AgentExecutionStep",
    "BaseAgent",
]
