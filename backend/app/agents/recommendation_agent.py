"""Engineering Recommendation Agent — Phase 6.

Generates a structured, prioritized list of building maintenance and repair
recommendations using the existing RecommendationPrompts.RECOMMENDATION_TEMPLATE.

Builds on:
    - rag_response: sources and KG context from RetrievalAgent
    - enriched_kg_context: multi-hop relationships from KGReasoningAgent
    - extracted_defects / extracted_components: from QueryAnalysisAgent

Decision recorded in trace:
    - reason: describes which defects drove the recommendations and how many
              high/medium/low priority actions were generated
    - confidence: based on source quality and LLM self-reported certainty

The LLM is called once to produce a recommendation block. The output is
parsed into typed EngineeringRecommendation objects (using the existing
response_parser logic) and stored in state["structured_recommendations"].
"""

import re
from typing import TYPE_CHECKING

from app.agents.base import BaseAgent
from app.agents.state import AgentExecutionStep, AgentTimer
from app.core.logging import get_logger
from app.prompts.recommendations import RecommendationPrompts
from app.schemas.chat import EngineeringRecommendation

if TYPE_CHECKING:
    from app.agents.state import AgentState
    from app.llm.base import BaseLLMProvider

logger = get_logger(__name__)

_PRIORITY_HIGH_RE = re.compile(r"\b(urgent|critical(?:ly)?|immediate(?:ly)?|high priority|must|severe)\b", re.I)
_PRIORITY_LOW_RE = re.compile(r"\b(optional|minor|low priority|consider|long.?term)\b", re.I)

_CATEGORY_MAP = {
    "investigation": ["inspect", "investigate", "test", "assess", "measure", "survey", "core", "rebound"],
    "repair": ["repair", "seal", "inject", "patch", "apply", "coat", "jacketing", "grouting", "retrofit", "epoxy"],
    "monitoring": ["monitor", "track", "observe", "record", "check", "gauge"],
    "replacement": ["replace", "demolish", "reconstruct", "remove", "renewal"],
    "further_analysis": ["analyse", "analyze", "study", "research", "consult", "structural audit"],
}


class RecommendationAgent(BaseAgent):
    """Generates prioritized engineering recommendations for building defects.

    Uses the LLM with existing RecommendationPrompts to produce a structured
    list of actions, each tagged with priority, category, and source reference.

    Args:
        llm_provider: Active LLM provider.
    """

    def __init__(self, llm_provider: "BaseLLMProvider") -> None:
        self._llm = llm_provider

    @property
    def name(self) -> str:
        return "RecommendationAgent"

    async def run(self, state: "AgentState") -> "AgentState":
        """Generate engineering recommendations from accumulated state context.

        Args:
            state: AgentState with rag_response and enriched_kg_context populated.

        Returns:
            Updated AgentState with structured_recommendations and recommendation_rationale.
        """
        timer = AgentTimer()
        timer.start()

        trace = list(state.get("execution_trace", []))

        # Skip if domain rejected
        if not state.get("is_building_domain", True):
            step = AgentExecutionStep(
                agent=self.name,
                status="skipped",
                time_ms=timer.elapsed_ms(),
                confidence=0.0,
                reason="Skipped: query rejected as non-building domain.",
            )
            trace.append(step)
            state["execution_trace"] = trace
            return state

        rag_response = state.get("rag_response")
        defects = state.get("extracted_defects", [])
        components = state.get("extracted_components", [])
        enriched_kg = state.get("enriched_kg_context", "")
        risk_chains = state.get("risk_chains", [])

        try:
            # --- Build defect_info block ---
            defect_parts = []
            if defects:
                defect_parts.append(f"**Identified Defects**: {', '.join(defects)}")
            if components:
                defect_parts.append(f"**Affected Components**: {', '.join(components)}")
            if risk_chains:
                for rc in risk_chains[:3]:
                    d = rc.get("defect", "")
                    r = rc.get("repair_method", "")
                    stds = ", ".join(rc.get("standards", []))
                    if d and r:
                        defect_parts.append(
                            f"- Defect '{d}' → Repair: '{r}'" + (f" [{stds}]" if stds else "")
                        )
            defect_info = "\n".join(defect_parts) if defect_parts else "No specific defects identified."

            # --- Build cause_analysis block from KG ---
            cause_parts = []
            if rag_response and rag_response.kg_context:
                for entity in rag_response.kg_context[:5]:
                    causes = [r.target for r in entity.relationships if r.type == "CAUSED_BY"]
                    if causes:
                        cause_parts.append(
                            f"- `{entity.entity}` caused by: {', '.join(causes[:3])}"
                        )
            if enriched_kg:
                cause_parts.append(enriched_kg[:800])
            cause_analysis = "\n".join(cause_parts) if cause_parts else "Root cause analysis not available."

            # --- Build available_context block ---
            context_parts = []
            if rag_response and rag_response.sources:
                for src in rag_response.sources[:3]:
                    context_parts.append(
                        f"- {src.document_name}"
                        + (f", Page {src.page}" if src.page else "")
                        + f" (relevance: {src.relevance_score:.2f})"
                    )
            available_context = "\n".join(context_parts) if context_parts else "No document sources available."

            # --- Call LLM ---
            prompt = RecommendationPrompts.RECOMMENDATION_TEMPLATE.format(
                defect_info=defect_info,
                cause_analysis=cause_analysis,
                available_context=available_context,
            )

            llm_response = await self._llm.generate(
                prompt=prompt,
                system_prompt=RecommendationPrompts.SYSTEM_PROMPT,
                max_tokens=1500,
            )
            recommendation_text = llm_response.content

            # --- Parse into structured EngineeringRecommendation objects ---
            structured = self._parse_recommendations(recommendation_text, rag_response)

            # --- Confidence: based on source quality and recommendation count ---
            source_quality = rag_response.confidence.score if rag_response else 0.0
            rec_count_bonus = min(0.10, len(structured) * 0.02)
            confidence = round(min(1.0, source_quality + rec_count_bonus), 3)

            # --- Reason summary ---
            high_count = sum(1 for r in structured if r.priority == "high")
            medium_count = sum(1 for r in structured if r.priority == "medium")
            low_count = sum(1 for r in structured if r.priority == "low")

            reason_parts = [
                f"Generated {len(structured)} recommendation(s) for defect(s): "
                f"{', '.join(defects[:3]) if defects else 'general building query'}."
            ]
            if high_count:
                reason_parts.append(f"{high_count} high-priority action(s) identified.")
            if medium_count:
                reason_parts.append(f"{medium_count} medium-priority action(s).")
            if low_count:
                reason_parts.append(f"{low_count} low-priority action(s).")
            if not structured:
                reason_parts.append("No structured recommendations could be parsed from LLM output.")

            reason = " ".join(reason_parts)

            step = AgentExecutionStep(
                agent=self.name,
                status="success",
                time_ms=timer.elapsed_ms(),
                confidence=confidence,
                reason=reason,
            )
            trace.append(step)

            state["structured_recommendations"] = structured
            state["recommendation_rationale"] = recommendation_text

            logger.info(
                "recommendation_agent_complete",
                recommendations=len(structured),
                confidence=confidence,
                high=high_count,
            )

        except Exception as exc:
            logger.error("recommendation_agent_failed", error=str(exc))
            step = AgentExecutionStep(
                agent=self.name,
                status="failed",
                time_ms=timer.elapsed_ms(),
                confidence=0.0,
                reason="RecommendationAgent failed during LLM call or parsing.",
                error=str(exc),
            )
            trace.append(step)
            # Fall back to existing recommendations from RAG response
            if rag_response and rag_response.recommendations:
                state["structured_recommendations"] = list(rag_response.recommendations)
            else:
                state["structured_recommendations"] = []
            state["recommendation_rationale"] = ""

        state["execution_trace"] = trace
        return state

    def _parse_recommendations(
        self,
        text: str,
        rag_response,
    ) -> list[EngineeringRecommendation]:
        """Parse LLM recommendation text into EngineeringRecommendation objects."""
        recommendations: list[EngineeringRecommendation] = []

        # Split on numbered list or bullet points
        items = re.split(r"\n\s*(?:\d+\.\s+|[-*•]\s+)", text)

        for item in items:
            item = item.strip()
            if len(item) < 20:
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
            for cat, kws in _CATEGORY_MAP.items():
                if any(kw in item_lower for kw in kws):
                    category = cat
                    break

            # Source reference — look for brackets or use first document source
            source_ref = None
            src_match = re.search(r"\[([^\]]{5,100})\]", item)
            if src_match:
                source_ref = src_match.group(1)
            elif rag_response and rag_response.sources:
                source_ref = rag_response.sources[0].document_name

            recommendations.append(
                EngineeringRecommendation(
                    action=item[:350].strip(),
                    priority=priority,
                    category=category,
                    source_reference=source_ref,
                )
            )

            if len(recommendations) >= 6:
                break

        return recommendations
