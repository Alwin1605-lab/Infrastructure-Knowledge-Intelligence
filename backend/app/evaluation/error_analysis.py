"""Error Analysis and Failure Classification for Phase 7 Evaluation.

Classifies why a benchmark failed into specific categories:
- Poor Retrieval (Hit rate 0, or low coverage)
- KG Missing (No KG context found but requested)
- Low LLM Confidence (LLM expressed uncertainty)
- No Engineering Standard Found (Standard requested but not in answer)
- Ambiguous Question (Query rejected or intent unclear)
- Missing Documents (No sources available)
"""

from typing import Any
from app.schemas.chat import ChatResponse


class ErrorAnalyzer:
    """Classifies failures during benchmark evaluations."""

    @staticmethod
    def classify_failure(
        question_category: str,
        expected_keywords: list[str],
        rag_response: ChatResponse | None,
        evaluation_results: dict[str, Any],
        agent_trace: list[dict[str, Any]] | None = None
    ) -> str:
        """Analyze state and metrics to determine the primary failure reason.

        Args:
            question_category: The category of the benchmark question.
            expected_keywords: Expected terms that were missing.
            rag_response: The ChatResponse object (if pipeline succeeded partially).
            evaluation_results: Dict of evaluation scores.
            agent_trace: Optional trace from AgentOrchestrator.

        Returns:
            String representing the primary failure category.
        """
        if not rag_response:
            # Check if domain was rejected
            if agent_trace and any(step.get("status") == "skipped" for step in agent_trace):
                return "Ambiguous Question / Domain Rejected"
            return "Pipeline Crash"

        # Check retrieval quality
        hit_rate = evaluation_results.get("hit_rate", {}).get("score", 1.0)
        coverage = evaluation_results.get("retrieval_coverage", {}).get("score", 1.0)
        if not rag_response.sources:
            return "Missing Documents"
        if hit_rate == 0.0 or coverage < 0.2:
            return "Poor Retrieval"

        # Check LLM confidence
        if rag_response.confidence.score < 0.4:
            return "Low LLM Confidence"

        # Check KG
        if not rag_response.kg_context and question_category == "defects":
            return "KG Missing"

        # Check completeness & standards
        completeness = evaluation_results.get("response_completeness", {}).get("score", 1.0)
        if completeness < 0.5:
            if question_category == "standards":
                return "No Engineering Standard Found"
            return "Incomplete LLM Reasoning"

        return "Unknown Failure"

    @staticmethod
    def is_failure(evaluation_results: dict[str, Any]) -> bool:
        """Determine if a result is considered a failure based on thresholds."""
        # Consider it a failure if completeness is < 50% or hit_rate is 0 (if measured)
        hit_rate = evaluation_results.get("hit_rate", {}).get("score", 1.0)
        completeness = evaluation_results.get("response_completeness", {}).get("score", 1.0)
        return hit_rate < 0.5 or completeness < 0.5
