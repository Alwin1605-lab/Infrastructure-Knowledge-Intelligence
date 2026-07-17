"""Research Evaluation Module.

Provides metrics and evaluators for measuring RAG system quality.
Designed for research experiments in the B.Tech project.

Usage:
    from app.evaluation import EvaluationSuite, RetrievalQualityEvaluator
    
    suite = EvaluationSuite()
    suite.add_evaluator(RetrievalQualityEvaluator())
    results = await suite.run(evaluation_data)
"""

from app.evaluation.base import BaseEvaluator, EvaluationResult, EvaluationSuite
from app.evaluation.metrics import (
    RetrievalQualityEvaluator,
    GroundingEvaluator,
    ConfidenceCalibrationEvaluator,
    LatencyEvaluator,
    AnswerRelevanceEvaluator,
)

__all__ = [
    "BaseEvaluator",
    "EvaluationResult",
    "EvaluationSuite",
    "RetrievalQualityEvaluator",
    "GroundingEvaluator",
    "ConfidenceCalibrationEvaluator",
    "LatencyEvaluator",
    "AnswerRelevanceEvaluator",
]
