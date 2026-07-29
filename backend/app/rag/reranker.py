"""Chunk Reranker for the Hybrid RAG Pipeline.

After ChromaDB returns chunks by cosine similarity, this reranker applies a
secondary scoring pass that boosts chunks containing extracted building entities
(defects, components, repair methods). This improves precision for domain-specific
queries where engineering terms are critical to relevance.

Design:
    - Pure Python, no ML model — deterministic and fast (< 2ms for 20 chunks).
    - Boost is additive: final_score = semantic_score + entity_overlap_boost.
    - Filtered results are re-sorted by final_score descending.
    - Original RetrievedChunk objects are never mutated.
"""

from dataclasses import dataclass

from app.core.logging import get_logger
from app.rag.query_processor import ProcessedQuery
from app.vectorstore.retriever import RetrievedChunk

logger = get_logger(__name__)

# Entity boost weight added to semantic similarity score
_ENTITY_BOOST = 0.08


@dataclass
class RankedChunk:
    """A retrieved chunk with its final reranked score.

    Attributes:
        chunk: The original RetrievedChunk from ChromaDB.
        semantic_score: Original cosine similarity score.
        entity_boost: Additive boost from entity overlap matching.
        final_score: Combined score used for final ranking.
        matched_entities: Entities from the query found in chunk text.
    """

    chunk: RetrievedChunk
    semantic_score: float
    entity_boost: float
    final_score: float
    matched_entities: list[str]


class ChunkReranker:
    """Reranks retrieved chunks by combining semantic score with entity overlap.

    Args:
        min_final_score: Minimum final score required to include a chunk.
    """

    def __init__(self, min_final_score: float = 0.20) -> None:
        self._min_final_score = min_final_score

    def rerank(
        self,
        chunks: list[RetrievedChunk],
        processed_query: ProcessedQuery,
    ) -> list[RankedChunk]:
        """Score and re-sort retrieved chunks.

        For each chunk, we:
            1. Take its original semantic relevance score.
            2. Add a boost for each extracted query entity found in the chunk text.
            3. Apply min_final_score filter.
            4. Return sorted by final_score descending.

        Args:
            chunks: List of chunks from ChromaDB retrieval.
            processed_query: Preprocessed query with extracted entities.

        Returns:
            List of RankedChunk sorted by final_score descending.
        """
        if not chunks:
            return []

        # Collect all entity terms to check presence in chunk text
        all_entity_terms = (
            processed_query.extracted_defects
            + processed_query.extracted_components
            + processed_query.extracted_repair_methods
            + processed_query.extracted_materials
        )

        ranked: list[RankedChunk] = []

        for chunk in chunks:
            chunk_lower = chunk.text.lower()
            matched = [term for term in all_entity_terms if term.lower() in chunk_lower]

            # Each matched entity contributes a fractional boost (capped at 0.30)
            boost = min(0.30, len(matched) * _ENTITY_BOOST)
            final_score = round(min(1.0, chunk.relevance_score + boost), 4)

            if final_score < self._min_final_score:
                logger.debug(
                    "chunk_filtered_by_reranker",
                    doc=chunk.document_name,
                    final_score=final_score,
                    threshold=self._min_final_score,
                )
                continue

            ranked.append(
                RankedChunk(
                    chunk=chunk,
                    semantic_score=chunk.relevance_score,
                    entity_boost=boost,
                    final_score=final_score,
                    matched_entities=matched,
                )
            )

        ranked.sort(key=lambda r: r.final_score, reverse=True)

        logger.info(
            "reranking_complete",
            input_chunks=len(chunks),
            output_chunks=len(ranked),
            top_score=ranked[0].final_score if ranked else 0.0,
        )

        return ranked
