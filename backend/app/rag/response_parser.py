"""Response Parser for the Hybrid RAG Pipeline.

Assembles a fully-typed ChatResponse from raw LLM text output, reranked chunks,
KG context data, confidence score, and timing information.

The LLM is prompted to produce structured Markdown with specific sections:
    ## Answer, ## Sources, ## Recommendations, ## Related Building Components, ## Confidence

This parser reads those sections and maps them to the ChatResponse schema.
It is deliberately tolerant — if a section is missing, sensible defaults are used
so the endpoint never fails due to LLM formatting variance.
"""

import re
import time
from typing import Any

from app.core.logging import get_logger
from app.rag.reranker import RankedChunk
from app.schemas.chat import (
    ChatResponse,
    ConfidenceScore,
    EngineeringRecommendation,
    KGEntityContext,
    KGRelationship,
    RelatedComponent,
    ResponseTime,
    SourceDocument,
)

logger = get_logger(__name__)

# Regex to find priority hints in recommendation text
_PRIORITY_HIGH_RE = re.compile(r"\b(urgent|critical|immediate|high priority|must)\b", re.I)
_PRIORITY_LOW_RE = re.compile(r"\b(optional|minor|low priority|consider)\b", re.I)

# Category keywords
_CATEGORY_MAP = {
    "investigation": ["inspect", "investigate", "test", "assess", "measure", "survey", "monitor"],
    "repair": ["repair", "seal", "inject", "patch", "apply", "coat", "jacketing", "grouting", "retrofit"],
    "monitoring": ["monitor", "track", "observe", "record", "check"],
    "replacement": ["replace", "demolish", "reconstruct", "remove"],
    "further_analysis": ["analyse", "analyze", "study", "research", "consult"],
}


class ResponseParser:
    """Parses LLM output into a fully-typed ChatResponse.

    Args:
        start_time_ns: Nanosecond timestamp from time.perf_counter_ns() at pipeline start.
        retrieval_ms: Time spent on vector retrieval.
        kg_lookup_ms: Time spent on KG traversal.
        llm_start_ns: Nanosecond timestamp just before LLM call.
    """

    def __init__(
        self,
        start_time_ns: int,
        retrieval_ms: float,
        kg_lookup_ms: float,
        llm_start_ns: int,
    ) -> None:
        self._start_ns = start_time_ns
        self._retrieval_ms = retrieval_ms
        self._kg_lookup_ms = kg_lookup_ms
        self._llm_start_ns = llm_start_ns

    def parse(
        self,
        llm_text: str,
        ranked_chunks: list[RankedChunk],
        kg_data: dict[str, Any],
        confidence: ConfidenceScore,
        question: str,
    ) -> ChatResponse:
        """Build a complete ChatResponse from LLM output and retrieval metadata.

        Args:
            llm_text: Raw text from the LLM.
            ranked_chunks: Reranked document chunks used for context.
            kg_data: Merged KG subgraph dict.
            confidence: Pre-computed ConfidenceScore.
            question: The original user question (for fallback answer).

        Returns:
            ChatResponse: Fully-typed structured response.
        """
        now_ns = time.perf_counter_ns()
        llm_ms = (now_ns - self._llm_start_ns) / 1_000_000
        post_start = time.perf_counter_ns()

        answer = self._extract_answer(llm_text, question)
        sources = self._build_sources(ranked_chunks)
        kg_context = self._build_kg_context(kg_data)
        recommendations = self._extract_recommendations(llm_text, ranked_chunks)
        related_components = self._build_related_components(kg_data, ranked_chunks)

        post_ms = (time.perf_counter_ns() - post_start) / 1_000_000
        total_ms = (time.perf_counter_ns() - self._start_ns) / 1_000_000

        response_time = ResponseTime(
            total_ms=round(total_ms, 1),
            retrieval_ms=round(self._retrieval_ms, 1),
            kg_lookup_ms=round(self._kg_lookup_ms, 1),
            llm_generation_ms=round(llm_ms, 1),
            post_processing_ms=round(post_ms, 1),
        )

        logger.info(
            "response_assembled",
            sources=len(sources),
            kg_context_entities=len(kg_context),
            recommendations=len(recommendations),
            total_ms=round(total_ms, 1),
        )

        return ChatResponse(
            answer=answer,
            sources=sources,
            kg_context=kg_context,
            confidence=confidence,
            recommendations=recommendations,
            related_components=related_components,
            response_time=response_time,
        )

    # ---------------------------------------------------------------------------
    # Private parsing helpers
    # ---------------------------------------------------------------------------

    def _extract_answer(self, llm_text: str, question: str) -> str:
        """Extract the main answer block from LLM output."""
        # Try to find an explicit "## Answer" or "**Answer**" section
        patterns = [
            r"#+\s*Answer[:\s]*\n+(.*?)(?=\n#+|\Z)",
            r"\*\*Answer\*\*[:\s]*\n+(.*?)(?=\n\*\*|\Z)",
        ]
        for pattern in patterns:
            match = re.search(pattern, llm_text, re.S | re.I)
            if match:
                text = match.group(1).strip()
                if len(text) > 30:
                    return text

        # Fall back: if the LLM just returned a paragraph, use the whole thing
        # Strip any trailing "Confidence:" section
        cleaned = re.sub(r"\n#+\s*(Confidence|Sources|Recommendations|Related).*", "", llm_text, flags=re.S | re.I)
        cleaned = cleaned.strip()
        if len(cleaned) > 30:
            return cleaned

        return f"I was unable to generate a structured answer for: \"{question}\""

    def _build_sources(self, ranked_chunks: list[RankedChunk]) -> list[SourceDocument]:
        """Build SourceDocument list from reranked chunks."""
        seen_chunks: set[str] = set()
        sources: list[SourceDocument] = []

        for rc in ranked_chunks:
            chunk = rc.chunk
            dedup_key = f"{chunk.document_name}:{chunk.chunk_index}"
            if dedup_key in seen_chunks:
                continue
            seen_chunks.add(dedup_key)

            sources.append(
                SourceDocument(
                    document_name=chunk.document_name,
                    page=chunk.page_number,
                    section=chunk.section,
                    chunk_preview=chunk.text[:200].strip() + ("..." if len(chunk.text) > 200 else ""),
                    relevance_score=rc.final_score,
                )
            )

        return sources

    def _build_kg_context(self, kg_data: dict[str, Any]) -> list[KGEntityContext]:
        """Convert merged KG subgraph dict into typed KGEntityContext list."""
        entities: list[KGEntityContext] = []

        # Process defect subgraphs
        for d in kg_data.get("defects_found", []):
            defect_name = d.get("defect", "")
            if not defect_name:
                continue
            rels: list[KGRelationship] = []
            for cause in d.get("causes", []):
                rels.append(KGRelationship(type="CAUSED_BY", target=cause, target_type="Cause"))
            for repair_obj in d.get("repairs", []):
                r_name = repair_obj.get("repair") if isinstance(repair_obj, dict) else str(repair_obj)
                if r_name:
                    rels.append(KGRelationship(type="REPAIRED_BY", target=r_name, target_type="RepairMethod"))
            for comp in d.get("affected_components", []):
                rels.append(KGRelationship(type="AFFECTS", target=comp, target_type="Component"))
            entities.append(KGEntityContext(entity=defect_name, type="Defect", relationships=rels))

        # Process component subgraphs
        for c in kg_data.get("components_found", []):
            comp_name = c.get("component", "")
            if not comp_name:
                continue
            rels = []
            for defect in c.get("affecting_defects", []):
                rels.append(KGRelationship(type="AFFECTED_BY", target=defect, target_type="Defect"))
            for mat in c.get("materials", []):
                rels.append(KGRelationship(type="MADE_OF", target=mat, target_type="Material"))
            entities.append(KGEntityContext(entity=comp_name, type="Component", relationships=rels))

        # Process generic entities
        for e in kg_data.get("entities", [])[:10]:
            name = e.get("name", "")
            etype = e.get("type", "Entity")
            if name and not any(ex.entity == name for ex in entities):
                entities.append(KGEntityContext(entity=name, type=etype, relationships=[]))

        return entities[:15]  # Cap at 15 entities

    def _extract_recommendations(
        self,
        llm_text: str,
        ranked_chunks: list[RankedChunk],
    ) -> list[EngineeringRecommendation]:
        """Extract engineering recommendations from LLM output."""
        recommendations: list[EngineeringRecommendation] = []

        # Look for a Recommendations section
        rec_match = re.search(
            r"#+\s*Recommendations?[:\s]*\n+(.*?)(?=\n#+|\Z)",
            llm_text, re.S | re.I
        )
        if not rec_match:
            rec_match = re.search(
                r"\*\*Recommendations?\*\*[:\s]*\n+(.*?)(?=\n\*\*|\Z)",
                llm_text, re.S | re.I
            )

        if rec_match:
            rec_block = rec_match.group(1)
            # Split on bullet points or numbered list
            items = re.split(r"\n\s*[-*•\d+\.]\s+", rec_block)
            for item in items:
                item = item.strip()
                if len(item) < 15:
                    continue

                # Infer priority
                if _PRIORITY_HIGH_RE.search(item):
                    priority = "high"
                elif _PRIORITY_LOW_RE.search(item):
                    priority = "low"
                else:
                    priority = "medium"

                # Infer category
                category = "further_analysis"
                item_lower = item.lower()
                for cat, keywords in _CATEGORY_MAP.items():
                    if any(kw in item_lower for kw in keywords):
                        category = cat
                        break

                # Find a source reference if one is cited
                source_ref = None
                src_match = re.search(r"\[([^\]]{5,80})\]", item)
                if src_match:
                    source_ref = src_match.group(1)
                elif ranked_chunks:
                    source_ref = ranked_chunks[0].chunk.document_name

                recommendations.append(
                    EngineeringRecommendation(
                        action=item[:300],
                        priority=priority,
                        category=category,
                        source_reference=source_ref,
                    )
                )

                if len(recommendations) >= 5:
                    break

        return recommendations

    def _build_related_components(
        self,
        kg_data: dict[str, Any],
        ranked_chunks: list[RankedChunk],
    ) -> list[RelatedComponent]:
        """Build related building components from KG component subgraphs."""
        components: list[RelatedComponent] = []
        seen: set[str] = set()

        for c in kg_data.get("components_found", []):
            name = c.get("component", "")
            if not name or name in seen:
                continue
            seen.add(name)

            components.append(
                RelatedComponent(
                    name=name.title(),
                    type="Structural Element",
                    related_defects=[d for d in c.get("affecting_defects", []) if d],
                    related_materials=[m for m in c.get("materials", []) if m],
                    connection=f"Building component identified in the Knowledge Graph with "
                               f"{len(c.get('affecting_defects', []))} associated defects.",
                )
            )

        return components[:5]
