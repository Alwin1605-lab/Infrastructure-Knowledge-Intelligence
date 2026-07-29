"""Concrete evaluation metrics for RAG system quality measurement.

Implements five research-grade evaluators:
    - RetrievalQualityEvaluator:        Precision@K of retrieved chunks
    - GroundingEvaluator:               Answer grounding in source documents
    - ConfidenceCalibrationEvaluator:   Confidence score calibration
    - LatencyEvaluator:                 Response time performance
    - AnswerRelevanceEvaluator:         Query-answer semantic similarity
"""

import math
from typing import Any

from app.evaluation.base import BaseEvaluator, EvaluationResult


class RetrievalQualityEvaluator(BaseEvaluator):
    """Measures precision and recall of retrieved document chunks.

    Compares retrieved chunk IDs against a ground-truth set of
    relevant chunk IDs to compute precision@k and recall.

    Required kwargs:
        retrieved_chunk_ids (list[str]): IDs of chunks returned by retrieval.
        relevant_chunk_ids (list[str]):  Ground-truth relevant chunk IDs.
    """

    @property
    def name(self) -> str:
        return "retrieval_quality"

    async def evaluate(self, **kwargs: Any) -> EvaluationResult:
        """Compute precision@k and recall.

        Args:
            retrieved_chunk_ids: List of retrieved chunk identifiers.
            relevant_chunk_ids: List of ground-truth relevant chunk identifiers.

        Returns:
            EvaluationResult with score = F1 of precision and recall.
        """
        retrieved: list[str] = kwargs.get("retrieved_chunk_ids", [])
        relevant: list[str] = kwargs.get("relevant_chunk_ids", [])

        if not retrieved or not relevant:
            return EvaluationResult(
                metric_name=self.name,
                score=0.0,
                details={
                    "precision": 0.0,
                    "recall": 0.0,
                    "f1": 0.0,
                    "k": len(retrieved),
                    "num_relevant": len(relevant),
                    "note": "Empty retrieved or relevant set",
                },
            )

        retrieved_set = set(retrieved)
        relevant_set = set(relevant)
        true_positives = retrieved_set & relevant_set

        precision = len(true_positives) / len(retrieved_set) if retrieved_set else 0.0
        recall = len(true_positives) / len(relevant_set) if relevant_set else 0.0

        # F1 score as the combined metric
        if precision + recall > 0:
            f1 = 2 * (precision * recall) / (precision + recall)
        else:
            f1 = 0.0

        return EvaluationResult(
            metric_name=self.name,
            score=f1,
            details={
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(f1, 4),
                "k": len(retrieved),
                "num_relevant": len(relevant),
                "true_positives": len(true_positives),
            },
        )


class GroundingEvaluator(BaseEvaluator):
    """Measures what fraction of the answer is supported by source documents.

    Uses a token-overlap heuristic: computes the ratio of unique words
    in the answer that also appear in the concatenated source texts.
    This is a lightweight proxy for grounding — a future version can
    use LLM-based evaluation for deeper semantic grounding checks.

    Required kwargs:
        answer (str):       The generated answer text.
        source_texts (list[str]): The source document chunks used.
    """

    @property
    def name(self) -> str:
        return "grounding"

    async def evaluate(self, **kwargs: Any) -> EvaluationResult:
        """Compute token-level grounding ratio.

        Args:
            answer: The generated answer text.
            source_texts: List of source document chunk texts.

        Returns:
            EvaluationResult with score = grounding ratio (0-1).
        """
        answer: str = kwargs.get("answer", "")
        source_texts: list[str] = kwargs.get("source_texts", [])

        if not answer:
            return EvaluationResult(
                metric_name=self.name,
                score=0.0,
                details={"grounding_ratio": 0.0, "note": "Empty answer"},
            )

        # Tokenize: lowercase, split on whitespace, filter short tokens
        answer_tokens = set(
            token.lower().strip(".,;:!?()[]{}\"'")
            for token in answer.split()
            if len(token.strip(".,;:!?()[]{}\"'")) > 2  # Skip tiny words
        )

        if not answer_tokens:
            return EvaluationResult(
                metric_name=self.name,
                score=0.0,
                details={"grounding_ratio": 0.0, "note": "No meaningful tokens"},
            )

        # Build source vocabulary
        source_vocab: set[str] = set()
        for text in source_texts:
            source_vocab.update(
                token.lower().strip(".,;:!?()[]{}\"'")
                for token in text.split()
                if len(token.strip(".,;:!?()[]{}\"'")) > 2
            )

        if not source_vocab:
            return EvaluationResult(
                metric_name=self.name,
                score=0.0,
                details={"grounding_ratio": 0.0, "note": "No source content"},
            )

        # Compute overlap ratio
        grounded_tokens = answer_tokens & source_vocab
        grounding_ratio = len(grounded_tokens) / len(answer_tokens)

        return EvaluationResult(
            metric_name=self.name,
            score=min(grounding_ratio, 1.0),
            details={
                "grounding_ratio": round(grounding_ratio, 4),
                "answer_unique_tokens": len(answer_tokens),
                "source_vocab_size": len(source_vocab),
                "grounded_tokens": len(grounded_tokens),
            },
        )


class ConfidenceCalibrationEvaluator(BaseEvaluator):
    """Measures whether the system's confidence scores are well-calibrated.

    Compares the predicted confidence against a binary correctness flag.
    A well-calibrated system should have high confidence for correct answers
    and low confidence for incorrect ones.

    The score is computed as: 1 - |predicted_confidence - actual_correctness|
    where actual_correctness is 1.0 if correct, 0.0 if incorrect.

    Required kwargs:
        predicted_confidence (float): The system's confidence score (0-1).
        is_correct (bool):            Whether the answer was actually correct.
    """

    @property
    def name(self) -> str:
        return "confidence_calibration"

    async def evaluate(self, **kwargs: Any) -> EvaluationResult:
        """Compute confidence calibration score.

        Args:
            predicted_confidence: System's confidence score (0-1).
            is_correct: Whether the answer was factually correct.

        Returns:
            EvaluationResult with score = calibration quality (0-1).
        """
        predicted: float = kwargs.get("predicted_confidence", 0.5)
        is_correct: bool = kwargs.get("is_correct", False)

        actual = 1.0 if is_correct else 0.0
        calibration_error = abs(predicted - actual)

        # Score: 1.0 means perfectly calibrated, 0.0 means worst case
        score = 1.0 - calibration_error

        return EvaluationResult(
            metric_name=self.name,
            score=score,
            details={
                "predicted_confidence": round(predicted, 4),
                "is_correct": is_correct,
                "calibration_error": round(calibration_error, 4),
                "interpretation": (
                    "well_calibrated" if calibration_error < 0.2
                    else "moderately_calibrated" if calibration_error < 0.5
                    else "poorly_calibrated"
                ),
            },
        )


class LatencyEvaluator(BaseEvaluator):
    """Evaluates response time performance against configurable thresholds.

    Scores the total response time on a smooth curve:
        - < excellent_ms:  score ≈ 1.0
        - < acceptable_ms: score ≈ 0.5-1.0
        - > acceptable_ms: score drops toward 0.0

    Required kwargs:
        response_time (dict): Response time breakdown with keys:
            total_ms, retrieval_ms, kg_lookup_ms,
            llm_generation_ms, post_processing_ms
    """

    def __init__(
        self,
        excellent_threshold_ms: float = 2000.0,
        acceptable_threshold_ms: float = 5000.0,
    ) -> None:
        """Initialize with latency thresholds.

        Args:
            excellent_threshold_ms: Below this is considered excellent.
            acceptable_threshold_ms: Above this is considered poor.
        """
        self._excellent_ms = excellent_threshold_ms
        self._acceptable_ms = acceptable_threshold_ms

    @property
    def name(self) -> str:
        return "latency"

    async def evaluate(self, **kwargs: Any) -> EvaluationResult:
        """Compute latency score from response time breakdown.

        Args:
            response_time: Dict with timing breakdown in milliseconds.

        Returns:
            EvaluationResult with score based on total_ms vs thresholds.
        """
        response_time: dict[str, float] = kwargs.get("response_time", {})
        total_ms = response_time.get("total_ms", float("inf"))

        # Sigmoid-like scoring: smooth transition between thresholds
        if total_ms <= self._excellent_ms:
            score = 1.0
        elif total_ms >= self._acceptable_ms * 2:
            score = 0.0
        else:
            # Linear interpolation between excellent and 2x acceptable
            score = 1.0 - (total_ms - self._excellent_ms) / (
                self._acceptable_ms * 2 - self._excellent_ms
            )
            score = max(0.0, min(1.0, score))

        # Determine performance tier
        if total_ms <= self._excellent_ms:
            tier = "excellent"
        elif total_ms <= self._acceptable_ms:
            tier = "acceptable"
        else:
            tier = "poor"

        return EvaluationResult(
            metric_name=self.name,
            score=round(score, 4),
            details={
                "total_ms": total_ms,
                "retrieval_ms": response_time.get("retrieval_ms", 0),
                "kg_lookup_ms": response_time.get("kg_lookup_ms", 0),
                "llm_generation_ms": response_time.get("llm_generation_ms", 0),
                "post_processing_ms": response_time.get("post_processing_ms", 0),
                "performance_tier": tier,
                "thresholds": {
                    "excellent_ms": self._excellent_ms,
                    "acceptable_ms": self._acceptable_ms,
                },
            },
        )


class AnswerRelevanceEvaluator(BaseEvaluator):
    """Measures semantic similarity between query and answer using embeddings.

    Computes cosine similarity between the query embedding and answer
    embedding vectors. Higher similarity indicates the answer is
    topically relevant to the question.

    Required kwargs:
        query_embedding (list[float]):  Embedding vector of the query.
        answer_embedding (list[float]): Embedding vector of the answer.
    """

    @property
    def name(self) -> str:
        return "answer_relevance"

    async def evaluate(self, **kwargs: Any) -> EvaluationResult:
        """Compute cosine similarity between query and answer embeddings.

        Args:
            query_embedding: Query embedding vector.
            answer_embedding: Answer embedding vector.

        Returns:
            EvaluationResult with score = cosine similarity (0-1).
        """
        query_emb: list[float] = kwargs.get("query_embedding", [])
        answer_emb: list[float] = kwargs.get("answer_embedding", [])

        if not query_emb or not answer_emb:
            return EvaluationResult(
                metric_name=self.name,
                score=0.0,
                details={
                    "cosine_similarity": 0.0,
                    "note": "Missing embedding vectors",
                },
            )

        if len(query_emb) != len(answer_emb):
            return EvaluationResult(
                metric_name=self.name,
                score=0.0,
                details={
                    "cosine_similarity": 0.0,
                    "note": (
                        f"Dimension mismatch: query={len(query_emb)}, "
                        f"answer={len(answer_emb)}"
                    ),
                },
            )

        # Compute cosine similarity
        dot_product = sum(q * a for q, a in zip(query_emb, answer_emb))
        query_norm = math.sqrt(sum(q * q for q in query_emb))
        answer_norm = math.sqrt(sum(a * a for a in answer_emb))

        if query_norm == 0 or answer_norm == 0:
            cosine_sim = 0.0
        else:
            cosine_sim = dot_product / (query_norm * answer_norm)

        # Clamp to [0, 1] — negative similarity treated as irrelevant
        score = max(0.0, min(1.0, cosine_sim))

        return EvaluationResult(
            metric_name=self.name,
            score=round(score, 4),
            details={
                "cosine_similarity": round(cosine_sim, 4),
                "embedding_dimension": len(query_emb),
                "interpretation": (
                    "highly_relevant" if score > 0.8
                    else "relevant" if score > 0.5
                    else "partially_relevant" if score > 0.3
                    else "low_relevance"
                ),
            },
        )


class RetrievalCoverageEvaluator(BaseEvaluator):
    """Measures retrieval coverage: percentage of expected keywords found in retrieved chunks."""

    @property
    def name(self) -> str:
        return "retrieval_coverage"

    async def evaluate(self, **kwargs: Any) -> EvaluationResult:
        expected_keywords: list[str] = kwargs.get("expected_keywords", [])
        retrieved_texts: list[str] = kwargs.get("retrieved_texts", [])

        if not expected_keywords:
            return EvaluationResult(metric_name=self.name, score=1.0, details={"note": "No expected keywords"})

        if not retrieved_texts:
            return EvaluationResult(metric_name=self.name, score=0.0, details={"note": "No chunks retrieved"})

        combined_text = " ".join(retrieved_texts).lower()
        found_count = sum(1 for kw in expected_keywords if kw.lower() in combined_text)
        coverage = found_count / len(expected_keywords)

        return EvaluationResult(
            metric_name=self.name,
            score=coverage,
            details={
                "coverage_percentage": round(coverage * 100, 2),
                "keywords_found": found_count,
                "keywords_total": len(expected_keywords),
            }
        )


class MRREvaluator(BaseEvaluator):
    """Mean Reciprocal Rank (MRR) for retrieved chunks."""

    @property
    def name(self) -> str:
        return "mrr"

    async def evaluate(self, **kwargs: Any) -> EvaluationResult:
        expected_chunk_ids: list[str] = kwargs.get("expected_chunk_ids", [])
        retrieved_chunk_ids: list[str] = kwargs.get("retrieved_chunk_ids", [])

        if not expected_chunk_ids:
            return EvaluationResult(self.name, score=0.0, details={"note": "No expected chunks provided"})

        score = 0.0
        rank = -1
        for i, chunk_id in enumerate(retrieved_chunk_ids, 1):
            if chunk_id in expected_chunk_ids:
                score = 1.0 / i
                rank = i
                break

        return EvaluationResult(
            self.name,
            score=round(score, 4),
            details={"first_relevant_rank": rank if rank > 0 else None}
        )


class HitRateEvaluator(BaseEvaluator):
    """Checks if ANY relevant context is in top-K."""

    @property
    def name(self) -> str:
        return "hit_rate"

    async def evaluate(self, **kwargs: Any) -> EvaluationResult:
        expected_chunk_ids: list[str] = kwargs.get("expected_chunk_ids", [])
        retrieved_chunk_ids: list[str] = kwargs.get("retrieved_chunk_ids", [])

        if not expected_chunk_ids:
            return EvaluationResult(self.name, score=0.0, details={"note": "No expected chunks provided"})

        hit = any(cid in expected_chunk_ids for cid in retrieved_chunk_ids)
        
        return EvaluationResult(
            self.name,
            score=1.0 if hit else 0.0,
            details={"hit": hit, "k_evaluated": len(retrieved_chunk_ids)}
        )


class CitationCorrectnessEvaluator(BaseEvaluator):
    """Validates if the cited sources actually contain the key claims of the answer."""

    @property
    def name(self) -> str:
        return "citation_correctness"

    async def evaluate(self, **kwargs: Any) -> EvaluationResult:
        # Simplified token matching implementation for now (could be LLM-based)
        cited_texts: list[str] = kwargs.get("cited_texts", [])
        answer_keywords: list[str] = kwargs.get("expected_keywords", [])

        if not cited_texts or not answer_keywords:
            return EvaluationResult(self.name, score=0.0, details={"note": "Missing inputs"})

        combined = " ".join(cited_texts).lower()
        supported = sum(1 for kw in answer_keywords if kw.lower() in combined)
        score = supported / len(answer_keywords)

        return EvaluationResult(self.name, score=round(score, 4), details={"supported_claims": supported})


class ResponseCompletenessEvaluator(BaseEvaluator):
    """Measures if all facets (expected keywords) were answered in the generated text."""

    @property
    def name(self) -> str:
        return "response_completeness"

    async def evaluate(self, **kwargs: Any) -> EvaluationResult:
        answer: str = kwargs.get("answer", "")
        expected_keywords: list[str] = kwargs.get("expected_keywords", [])

        if not expected_keywords:
            return EvaluationResult(self.name, score=1.0, details={"note": "No expectations"})
        
        lower_ans = answer.lower()
        found = sum(1 for kw in expected_keywords if kw.lower() in lower_ans)
        score = found / len(expected_keywords)

        return EvaluationResult(self.name, score=round(score, 4), details={"keywords_found": found})


class RecommendationQualityEvaluator(BaseEvaluator):
    """Evaluates presence and priority of recommendations."""

    @property
    def name(self) -> str:
        return "recommendation_quality"

    async def evaluate(self, **kwargs: Any) -> EvaluationResult:
        recs: list = kwargs.get("recommendations", [])
        if not recs:
            return EvaluationResult(self.name, score=0.0, details={"note": "No recommendations generated"})

        # Score based on presence of high/medium priority actions
        high = sum(1 for r in recs if getattr(r, "priority", "low") == "high")
        score = min(1.0, 0.5 + (0.1 * len(recs)) + (0.2 * high))
        
        return EvaluationResult(self.name, score=round(score, 4), details={"total_recs": len(recs), "high_priority": high})

