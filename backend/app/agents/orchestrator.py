"""Agent Orchestrator — Phase 6.

Manages the full 5-agent pipeline using a sequential execution graph.
Handles routing, conditional skipping, per-agent retries, and final response assembly.

Pipeline order:
    QueryAnalysisAgent → RetrievalAgent → KGReasoningAgent
        → RecommendationAgent → ReportAgent

Conditional routing:
    - If QueryAnalysisAgent marks is_building_domain=False:
        → All downstream agents are SKIPPED
        → Returns a polite rejection AgentPipelineResponse immediately
    - If any agent FAILS:
        → Marks that step as failed in trace
        → Continues pipeline with best available state
        → Pipeline never raises to the caller

Stateless design:
    - A fresh AgentState is created per query via new_agent_state()
    - No session memory, no conversation history, no persistent state
    - Every call is fully independent

Retry policy:
    - Up to MAX_RETRIES retries for RetrievalAgent and RecommendationAgent
    - Other agents are not retried (fast, or errors are non-fatal)
"""

import time
from typing import Any, TYPE_CHECKING

from app.agents.base import BaseAgent
from app.agents.state import AgentExecutionStep, AgentState, AgentTimer, new_agent_state
from app.agents.query_analysis_agent import QueryAnalysisAgent
from app.agents.retrieval_agent import RetrievalAgent
from app.agents.kg_reasoning_agent import KGReasoningAgent
from app.agents.recommendation_agent import RecommendationAgent
from app.agents.report_agent import ReportAgent
from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.embedding.huggingface import HuggingFaceEmbeddingService
    from app.llm.base import BaseLLMProvider
    from app.rag.pipeline import HybridRAGPipeline

logger = get_logger(__name__)

MAX_RETRIES = 2
PIPELINE_VERSION = "6.0"


class AgentOrchestrator:
    """Manages and executes the 5-agent Building Knowledge Intelligence pipeline.

    Initializes all agents once at startup and reuses them for every query.
    Each query produces a fresh AgentState with no shared mutable state.

    Args:
        llm_provider: Active LLM provider (Groq or Ollama).
        rag_pipeline: Initialized HybridRAGPipeline from Phase 5.
    """

    def __init__(
        self,
        llm_provider: "BaseLLMProvider",
        rag_pipeline: "HybridRAGPipeline",
    ) -> None:
        # Initialize agents (stateless — safe to reuse across requests)
        self._query_agent = QueryAnalysisAgent(llm_provider=llm_provider)
        self._retrieval_agent = RetrievalAgent(rag_pipeline=rag_pipeline)
        self._kg_agent = KGReasoningAgent()
        self._recommendation_agent = RecommendationAgent(llm_provider=llm_provider)
        self._report_agent = ReportAgent(llm_provider=llm_provider)

        # Ordered pipeline (immutable after init)
        self._pipeline: list[BaseAgent] = [
            self._query_agent,
            self._retrieval_agent,
            self._kg_agent,
            self._recommendation_agent,
            self._report_agent,
        ]

        logger.info(
            "agent_orchestrator_initialized",
            agents=[a.name for a in self._pipeline],
            version=PIPELINE_VERSION,
        )

    async def run(
        self,
        question: str,
        top_k: int = 5,
        include_kg: bool = True,
        workspace_id: str | None = None,
    ) -> dict[str, Any]:
        """Execute the full 5-agent pipeline for a user query.

        Creates a fresh stateless AgentState, runs all agents sequentially,
        and assembles the final AgentPipelineResponse dict.

        Args:
            question: The raw user question about building engineering.
            top_k: Number of document chunks to retrieve.
            include_kg: Whether to run KG reasoning agent.

        Returns:
            dict: Fully assembled response matching AgentPipelineResponse schema.
                  Never raises — errors are captured in the execution trace.
        """
        pipeline_start_ns = time.perf_counter_ns()

        # --- Fresh stateless state ---
        state = new_agent_state(question=question, top_k=top_k, include_kg=include_kg)
        state["workspace_id"] = workspace_id
        session_id = state["session_id"]

        logger.info(
            "agent_pipeline_start",
            session_id=session_id,
            question=question[:80],
            top_k=top_k,
        )

        # --- Agents with retry policy ---
        retryable = {self._retrieval_agent.name, self._recommendation_agent.name}

        for agent in self._pipeline:
            # Early exit after domain rejection
            if not state.get("is_building_domain", True) and agent.name != self._query_agent.name:
                # All downstream agents will record themselves as skipped internally
                pass

            state = await self._run_agent_with_retry(
                agent=agent,
                state=state,
                max_retries=MAX_RETRIES if agent.name in retryable else 1,
            )

        # --- Assemble final response ---
        pipeline_ms = (time.perf_counter_ns() - pipeline_start_ns) / 1_000_000
        response = self._assemble_response(state=state, pipeline_ms=pipeline_ms)

        logger.info(
            "agent_pipeline_complete",
            session_id=session_id,
            total_ms=round(pipeline_ms, 1),
            agents_run=len([s for s in state.get("execution_trace", []) if s.status != "skipped"]),
            confidence=response.get("overall_confidence", 0.0),
        )

        return response

    # ---------------------------------------------------------------------------
    # Private helpers
    # ---------------------------------------------------------------------------

    async def _run_agent_with_retry(
        self,
        agent: BaseAgent,
        state: AgentState,
        max_retries: int = 1,
    ) -> AgentState:
        """Run an agent with retry on failure.

        On the first successful run, the agent's trace step is marked success.
        If all retries fail, the last failed step remains in the trace.

        Args:
            agent: The agent to execute.
            state: Current AgentState.
            max_retries: Maximum execution attempts.

        Returns:
            Updated AgentState from the last run.
        """
        for attempt in range(1, max_retries + 1):
            try:
                state = await agent.run(state)
                # If the agent recorded failure and we can retry, remove the trace step
                trace = list(state.get("execution_trace", []))
                if trace and trace[-1].agent == agent.name and trace[-1].status == "failed":
                    if attempt < max_retries:
                        logger.warning(
                            "agent_retry",
                            agent=agent.name,
                            attempt=attempt,
                            error=trace[-1].error,
                        )
                        # Remove failed step — will be replaced by next attempt's step
                        state["execution_trace"] = trace[:-1]
                        continue
                break  # Success or final failure
            except Exception as exc:
                # Agents should never raise, but this is a safety net
                logger.error("agent_unexpected_exception", agent=agent.name, error=str(exc))
                trace = list(state.get("execution_trace", []))
                trace.append(
                    AgentExecutionStep(
                        agent=agent.name,
                        status="failed",
                        time_ms=0.0,
                        confidence=0.0,
                        reason="Agent raised an unexpected exception.",
                        error=str(exc),
                    )
                )
                state["execution_trace"] = trace
                break

        return state

    def _assemble_response(self, state: AgentState, pipeline_ms: float) -> dict[str, Any]:
        """Assemble the final AgentPipelineResponse from completed state.

        Args:
            state: Fully executed AgentState.
            pipeline_ms: Total wall-clock pipeline time.

        Returns:
            dict matching AgentPipelineResponse schema.
        """
        trace = state.get("execution_trace", [])
        rag_response = state.get("rag_response")

        # Rejection case
        if not state.get("is_building_domain", True):
            return {
                "session_id": state.get("session_id", ""),
                "question": state.get("original_question", ""),
                "rag_response": None,
                "report": state.get("rejection_reason", "Query outside building domain."),
                "execution_trace": [s.to_dict() for s in trace],
                "total_agents_run": sum(1 for s in trace if s.status == "success"),
                "total_pipeline_ms": round(pipeline_ms, 1),
                "pipeline_version": PIPELINE_VERSION,
                "overall_confidence": 0.0,
                "domain_valid": False,
            }

        # Compute overall confidence as weighted average of agent confidences
        successful_steps = [s for s in trace if s.status == "success"]
        overall_confidence = (
            round(sum(s.confidence for s in successful_steps) / len(successful_steps), 3)
            if successful_steps else 0.0
        )

        # Merge agent recommendations into rag_response if better ones were generated
        if rag_response and state.get("structured_recommendations"):
            # Replace rag_response recommendations with agent-generated ones
            rag_response.recommendations = list(state["structured_recommendations"])

        return {
            "session_id": state.get("session_id", ""),
            "question": state.get("original_question", ""),
            "rag_response": rag_response,
            "report": state.get("report_text", ""),
            "execution_trace": [s.to_dict() for s in trace],
            "total_agents_run": sum(1 for s in trace if s.status == "success"),
            "total_pipeline_ms": round(pipeline_ms, 1),
            "pipeline_version": PIPELINE_VERSION,
            "overall_confidence": overall_confidence,
            "domain_valid": True,
            "query_intent": state.get("query_intent", "general"),
            "enriched_kg_available": bool(state.get("enriched_kg_context", "")),
        }

    async def health(self) -> dict[str, Any]:
        """Return orchestrator health status."""
        return {
            "status": "healthy",
            "orchestrator": "AgentOrchestrator",
            "version": PIPELINE_VERSION,
            "pipeline": [a.name for a in self._pipeline],
            "stateless": True,
            "retry_policy": f"max {MAX_RETRIES} retries for RetrievalAgent, RecommendationAgent",
        }
