"""Confidence Scorer for the Hybrid RAG Pipeline.

Computes a structured ConfidenceScore for each AI response based on:
    - Number and quality of retrieved document chunks
    - Presence of Knowledge Graph entities and relationships
    - Grounding type (rag_and_kg, rag_only, kg_only, insufficient_context)

Scoring logic:
    base_score = max semantic relevance of top chunk (0–1.0)
    kg_bonus   = +0.10 if ≥1 KG entity found, +0.05 for each additional (max 0.20)
    source_pen = −0.15 if only 1 source, −0.30 if 0 sources
    final      = clamp(base_score + kg_bonus + source_pen, 0.0, 1.0)
"""

from app.core.logging import get_logger
from app.rag.reranker import RankedChunk
from app.schemas.chat import ConfidenceScore

logger = get_logger(__name__)


class ConfidenceScorer:
    """Computes confidence score and grounding type for a RAG response.

    This class is deterministic and performs no I/O.
    """

    def score(
        self,
        ranked_chunks: list[RankedChunk],
        num_kg_entities: int,
        question: str,
    ) -> ConfidenceScore:
        """Compute a ConfidenceScore for the given retrieval results.

        Args:
            ranked_chunks: Reranked document chunks from ChromaRetriever.
            num_kg_entities: Number of KG entities found for this query.
            question: The user's question (for logging).

        Returns:
            ConfidenceScore with numeric score, level, grounding, and reasoning.
        """
        num_chunks = len(ranked_chunks)
        top_score = ranked_chunks[0].final_score if ranked_chunks else 0.0

        # --- Base score from vector retrieval ---
        # Normalize dense vector similarity (in high-dim embedding space, 0.55-0.75 indicates strong relevance)
        if num_chunks >= 3:
            base = min(0.90, max(0.50, top_score * 1.15))
        elif num_chunks > 0:
            base = min(0.80, max(0.40, top_score * 1.05))
        else:
            base = 0.0

        # --- KG bonus ---
        kg_bonus = 0.0
        if num_kg_entities >= 1:
            kg_bonus = min(0.15, 0.08 + (num_kg_entities - 1) * 0.03)

        # --- Source penalty ---
        source_penalty = 0.0
        if num_chunks == 0:
            source_penalty = -0.40
        elif num_chunks == 1:
            source_penalty = -0.05

        # --- Final score ---
        final = round(max(0.0, min(0.99, base + kg_bonus + source_penalty)), 3)

        # --- Grounding type ---
        if num_chunks > 0 and num_kg_entities > 0:
            grounding = "rag_and_kg"
        elif num_chunks > 0:
            grounding = "rag_only"
        elif num_kg_entities > 0:
            grounding = "kg_only"
        else:
            grounding = "insufficient_context"

        # --- Confidence level ---
        if final >= 0.75:
            level = "high"
        elif final >= 0.50:
            level = "medium"
        elif final >= 0.25:
            level = "low"
        else:
            level = "insufficient"

        # --- Reasoning string ---
        parts: list[str] = []
        if num_chunks > 0:
            parts.append(f"{num_chunks} document chunk(s) retrieved (top score: {top_score:.2f})")
        else:
            parts.append("No relevant document chunks found in the knowledge base")
        if num_kg_entities > 0:
            parts.append(f"{num_kg_entities} Knowledge Graph entities matched")
        else:
            parts.append("No KG entities matched this query")
        reasoning = ". ".join(parts) + "."

        confidence = ConfidenceScore(
            score=final,
            level=level,
            grounding=grounding,
            reasoning=reasoning,
        )

        logger.debug(
            "confidence_scored",
            final=final,
            level=level,
            grounding=grounding,
            chunks=num_chunks,
            kg_entities=num_kg_entities,
        )

        return confidence
