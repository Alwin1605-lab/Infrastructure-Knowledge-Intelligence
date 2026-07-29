"""Retrieval Agent — Phase 6.

Calls the existing Phase 5 HybridRAGPipeline.query() with the reformulated
query from QueryAnalysisAgent. Stores the full ChatResponse in state.

Decision recorded in trace:
    - reason: reports number of sources found, top relevance score, and grounding type
    - confidence: directly derived from the RAG pipeline's confidence score

This agent does NOT duplicate RAG logic — it delegates entirely to the
existing HybridRAGPipeline and records the result in AgentState.
"""

from typing import TYPE_CHECKING

from app.agents.base import BaseAgent
from app.agents.state import AgentExecutionStep, AgentTimer
from app.core.logging import get_logger
from app.schemas.chat import ChatRequest

if TYPE_CHECKING:
    from app.agents.state import AgentState
    from app.rag.pipeline import HybridRAGPipeline

logger = get_logger(__name__)


class RetrievalAgent(BaseAgent):
    """Orchestrates the Hybrid RAG pipeline for document and KG retrieval.

    Uses the reformulated query from QueryAnalysisAgent to call the full
    Phase 5 HybridRAGPipeline. The resulting ChatResponse is stored in
    state["rag_response"] for use by downstream agents.

    Args:
        rag_pipeline: The initialized HybridRAGPipeline instance.
    """

    def __init__(self, rag_pipeline: "HybridRAGPipeline") -> None:
        self._pipeline = rag_pipeline

    @property
    def name(self) -> str:
        return "RetrievalAgent"

    async def run(self, state: "AgentState") -> "AgentState":
        """Execute hybrid RAG retrieval and store ChatResponse in state.

        Args:
            state: Current AgentState with reformulated_query populated.

        Returns:
            Updated AgentState with rag_response set.
        """
        timer = AgentTimer()
        timer.start()

        trace = list(state.get("execution_trace", []))

        # Skip if domain was already rejected
        if not state.get("is_building_domain", True):
            step = AgentExecutionStep(
                agent=self.name,
                status="skipped",
                time_ms=timer.elapsed_ms(),
                confidence=0.0,
                reason="Skipped: query was rejected as non-building domain by QueryAnalysisAgent.",
            )
            trace.append(step)
            state["execution_trace"] = trace
            return state

        query = state.get("reformulated_query") or state.get("original_question", "")
        top_k = state.get("top_k", 5)
        include_kg = state.get("include_kg", True)

        try:
            request = ChatRequest(
                question=query,
                top_k=top_k,
                include_kg_context=include_kg,
            )
            rag_response = await self._pipeline.query(request)

            state["rag_response"] = rag_response

            # Build reason from response stats
            num_sources = len(rag_response.sources)
            grounding = rag_response.confidence.grounding
            conf_score = rag_response.confidence.score
            top_relevance = (
                max(s.relevance_score for s in rag_response.sources)
                if rag_response.sources else 0.0
            )

            reason_parts = [
                f"Retrieved {num_sources} source chunk(s) with top relevance {top_relevance:.2f}.",
                f"Grounding: {grounding}.",
            ]
            if rag_response.kg_context:
                reason_parts.append(
                    f"Knowledge Graph returned {len(rag_response.kg_context)} entity context(s)."
                )
            else:
                reason_parts.append("No KG entities matched this query.")

            if num_sources == 0:
                reason_parts.append("No document chunks passed the similarity threshold.")

            reason = " ".join(reason_parts)
            confidence = round(conf_score, 3)

            step = AgentExecutionStep(
                agent=self.name,
                status="success",
                time_ms=timer.elapsed_ms(),
                confidence=confidence,
                reason=reason,
            )
            trace.append(step)

            logger.info(
                "retrieval_agent_complete",
                sources=num_sources,
                grounding=grounding,
                confidence=confidence,
            )

        except Exception as exc:
            logger.error("retrieval_agent_failed", error=str(exc))
            step = AgentExecutionStep(
                agent=self.name,
                status="failed",
                time_ms=timer.elapsed_ms(),
                confidence=0.0,
                reason="RetrievalAgent failed during hybrid RAG pipeline execution.",
                error=str(exc),
            )
            trace.append(step)

        state["execution_trace"] = trace
        return state
