"""Context Fusion for the Hybrid RAG Pipeline.

Merges vector-retrieved document chunks with structured Knowledge Graph subgraph data
into a single, coherent LLM prompt context. Uses existing:
    - app/prompts/rag.py: RAGPrompts templates
    - app/knowledge_graph/queries.py: format_kg_context_for_rag()
    - app/vectorstore/retriever.py: RetrievedChunk.to_citation_string()

This module is the "translation layer" — it converts raw retrieval results into
structured text that the LLM can reason over.
"""

from dataclasses import dataclass, field
from typing import Any

from app.core.logging import get_logger
from app.prompts.rag import RAGPrompts
from app.knowledge_graph.queries import format_kg_context_for_rag
from app.rag.reranker import RankedChunk

logger = get_logger(__name__)

# Maximum characters for document context block injected into the prompt
_MAX_DOC_CONTEXT_CHARS = 8000
# Maximum characters for KG context block
_MAX_KG_CONTEXT_CHARS = 2000


@dataclass
class FusedContext:
    """The assembled context ready for LLM injection.

    Attributes:
        document_context: Formatted string of retrieved chunks with citations.
        kg_context: Formatted string of KG entities and relationships.
        full_prompt: The complete user prompt (QUERY_TEMPLATE filled in).
        num_chunks: Number of chunks included.
        num_kg_entities: Number of KG entities found.
        has_sufficient_context: True if retrieval found meaningful content.
    """

    document_context: str
    kg_context: str
    full_prompt: str
    num_chunks: int
    num_kg_entities: int
    has_sufficient_context: bool
    ranked_chunks: list[RankedChunk] = field(default_factory=list)
    raw_kg_data: dict[str, Any] = field(default_factory=dict)


class ContextFuser:
    """Merges vector and graph retrieval results into a structured LLM prompt.

    This class is stateless — it only formats data and has no I/O dependencies.
    """

    def fuse(
        self,
        ranked_chunks: list[RankedChunk],
        kg_subgraphs: list[dict[str, Any]],
        question: str,
    ) -> FusedContext:
        """Build a fused context from retrieval results.

        Args:
            ranked_chunks: Reranked document chunks from ChromaDB.
            kg_subgraphs: List of KG subgraph dicts from queries.py.
            question: The original user question.

        Returns:
            FusedContext with formatted document context, KG context, and full prompt.
        """
        # --- Document context ---
        doc_context = self._format_document_context(ranked_chunks)

        # --- KG context ---
        merged_kg: dict[str, Any] = {}
        for sg in kg_subgraphs:
            if not sg:
                continue
            if "defects_found" in sg:
                merged_kg.setdefault("defects_found", []).extend(sg["defects_found"])
            elif "components_found" in sg:
                merged_kg.setdefault("components_found", []).extend(sg["components_found"])
            elif "entities" in sg:
                merged_kg.setdefault("entities", []).extend(sg.get("entities", []))
                merged_kg.setdefault("relationships", []).extend(sg.get("relationships", []))
            else:
                # Raw entity list from search_entities_by_text
                if isinstance(sg, list):
                    merged_kg.setdefault("entities", []).extend(sg)

        kg_context = format_kg_context_for_rag(merged_kg)
        # Truncate if too large
        if len(kg_context) > _MAX_KG_CONTEXT_CHARS:
            kg_context = kg_context[:_MAX_KG_CONTEXT_CHARS] + "\n\n[KG context truncated for length]"

        # Count KG entities
        num_kg_entities = (
            len(merged_kg.get("defects_found", []))
            + len(merged_kg.get("components_found", []))
            + len(merged_kg.get("entities", []))
        )

        # --- Determine if context is sufficient ---
        has_sufficient = bool(ranked_chunks) or num_kg_entities > 0

        # --- Build LLM prompt using existing RAGPrompts template ---
        if has_sufficient:
            full_prompt = RAGPrompts.QUERY_TEMPLATE.format(
                document_context=doc_context,
                kg_context=kg_context,
                question=question,
            )
        else:
            full_prompt = RAGPrompts.INSUFFICIENT_CONTEXT_RESPONSE.format(
                question=question,
                num_chunks_retrieved=0,
                num_kg_entities=0,
                suggested_documents="CPWD Maintenance Manual, NBC sections, Structural Audit Reports",
            )

        logger.debug(
            "context_fusion_complete",
            num_chunks=len(ranked_chunks),
            num_kg_entities=num_kg_entities,
            doc_context_chars=len(doc_context),
            kg_context_chars=len(kg_context),
            has_sufficient=has_sufficient,
        )

        return FusedContext(
            document_context=doc_context,
            kg_context=kg_context,
            full_prompt=full_prompt,
            num_chunks=len(ranked_chunks),
            num_kg_entities=num_kg_entities,
            has_sufficient_context=has_sufficient,
            ranked_chunks=ranked_chunks,
            raw_kg_data=merged_kg,
        )

    def _format_document_context(self, ranked_chunks: list[RankedChunk]) -> str:
        """Format reranked chunks into a numbered, citation-annotated context string."""
        if not ranked_chunks:
            return "No relevant building engineering documents found in the knowledge base."

        parts: list[str] = []
        total_chars = 0

        for i, rc in enumerate(ranked_chunks, 1):
            chunk = rc.chunk
            citation = chunk.to_citation_string()
            entry = (
                f"**[Source {i}]** {citation} "
                f"(semantic: {rc.semantic_score:.2f}, "
                f"reranked: {rc.final_score:.2f})\n\n"
                f"{chunk.text}"
            )

            # Stop if we would exceed the character budget
            if total_chars + len(entry) > _MAX_DOC_CONTEXT_CHARS:
                parts.append(
                    f"**[Source {i}+]** Additional sources truncated to fit context window."
                )
                break

            parts.append(entry)
            total_chars += len(entry)

        return "\n\n---\n\n".join(parts)
