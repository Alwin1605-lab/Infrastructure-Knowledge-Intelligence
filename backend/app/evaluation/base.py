"""Base evaluation infrastructure for research experiments.

Provides the foundation for measuring RAG system quality, grounding fidelity,
and system performance. Designed for the B.Tech research project to enable
systematic evaluation of the Knowledge Graph + RAG fusion approach.

Architecture:
    EvaluationResult  — Standardized metric output (dataclass)
    BaseEvaluator     — Abstract base for all evaluators
    EvaluationSuite   — Orchestrator that runs multiple evaluators
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class EvaluationResult:
    """Standardized result from a single evaluation metric.

    Attributes:
        metric_name: Human-readable name of the metric (e.g., "retrieval_quality").
        score: Normalized score between 0.0 and 1.0 (higher is better).
        details: Metric-specific details (e.g., precision, recall, breakdown).
        timestamp: When the evaluation was performed (UTC).
    """

    metric_name: str
    score: float
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Validate score is within [0, 1] range."""
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(
                f"Score must be between 0.0 and 1.0, got {self.score} "
                f"for metric '{self.metric_name}'"
            )

    def to_dict(self) -> dict[str, Any]:
        """Convert to a JSON-serializable dictionary."""
        return {
            "metric_name": self.metric_name,
            "score": round(self.score, 4),
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }


class BaseEvaluator(ABC):
    """Abstract base class for all evaluation metrics.

    Each evaluator implements a single metric. Evaluators are stateless
    and can be reused across multiple evaluation runs.

    Subclasses must implement:
        - name: Property returning the metric name.
        - evaluate: Async method computing the metric.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the human-readable metric name."""
        ...

    @abstractmethod
    async def evaluate(self, **kwargs: Any) -> EvaluationResult:
        """Compute the evaluation metric.

        Args:
            **kwargs: Metric-specific inputs (e.g., retrieved_chunks,
                      answer_text, source_texts).

        Returns:
            EvaluationResult with the computed score and details.
        """
        ...


class EvaluationSuite:
    """Orchestrator for running multiple evaluators as a batch.

    Collects evaluators and runs them against the same input data,
    producing a consolidated report of all metrics.

    Usage:
        suite = EvaluationSuite()
        suite.add_evaluator(RetrievalQualityEvaluator())
        suite.add_evaluator(GroundingEvaluator())
        results = await suite.run(answer="...", sources=[...])
    """

    def __init__(self) -> None:
        """Initialize an empty evaluation suite."""
        self._evaluators: list[BaseEvaluator] = []

    def add_evaluator(self, evaluator: BaseEvaluator) -> "EvaluationSuite":
        """Add an evaluator to the suite.

        Args:
            evaluator: An evaluator instance to include in the suite.

        Returns:
            Self for method chaining.
        """
        self._evaluators.append(evaluator)
        logger.debug("evaluator_added", evaluator=evaluator.name)
        return self

    @property
    def evaluator_names(self) -> list[str]:
        """List names of all registered evaluators."""
        return [e.name for e in self._evaluators]

    async def run(self, **kwargs: Any) -> list[EvaluationResult]:
        """Run all evaluators and collect results.

        Each evaluator receives the same kwargs. If an evaluator fails,
        a result with score 0.0 and the error details is recorded.

        Args:
            **kwargs: Inputs passed to each evaluator's evaluate() method.

        Returns:
            List of EvaluationResult from each evaluator.
        """
        results: list[EvaluationResult] = []

        for evaluator in self._evaluators:
            try:
                result = await evaluator.evaluate(**kwargs)
                results.append(result)
                logger.debug(
                    "evaluation_completed",
                    metric=evaluator.name,
                    score=result.score,
                )
            except Exception as exc:
                logger.error(
                    "evaluation_failed",
                    metric=evaluator.name,
                    error=str(exc),
                )
                results.append(
                    EvaluationResult(
                        metric_name=evaluator.name,
                        score=0.0,
                        details={"error": str(exc), "status": "failed"},
                    )
                )

        return results

    async def run_and_summarize(self, **kwargs: Any) -> dict[str, Any]:
        """Run all evaluators and return a summary dictionary.

        Args:
            **kwargs: Inputs passed to each evaluator's evaluate() method.

        Returns:
            Dictionary with 'metrics' (individual results), 'overall_score'
            (average across all metrics), and 'timestamp'.
        """
        results = await self.run(**kwargs)

        scores = [r.score for r in results]
        overall_score = sum(scores) / len(scores) if scores else 0.0

        return {
            "overall_score": round(overall_score, 4),
            "num_metrics": len(results),
            "metrics": {r.metric_name: r.to_dict() for r in results},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
