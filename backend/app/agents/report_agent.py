"""Report Generation Agent — Phase 6.

Synthesizes all accumulated state into a structured engineering report using
the existing ReportPrompts.REPORT_TEMPLATE. This is the final agent in the
pipeline and produces the deliverable engineering document.

Decision recorded in trace:
    - reason: describes what sections were populated and the overall condition
              rating inferred from confidence and priority levels
    - confidence: based on completeness of the input data and LLM self-assessment

The report follows CPWD/building standards structure:
    1. Executive Summary (overall condition rating)
    2. Building Component Assessment (defects, severity, locations)
    3. Root Cause Analysis (causes from KG reasoning)
    4. Repair and Maintenance Recommendations (from RecommendationAgent)
    5. Risk Matrix (risks from KG traversal)
    6. References (cited sources from RAG)
"""

import re
from typing import TYPE_CHECKING

from app.agents.base import BaseAgent
from app.agents.state import AgentExecutionStep, AgentTimer
from app.core.logging import get_logger
from app.prompts.reports import ReportPrompts

if TYPE_CHECKING:
    from app.agents.state import AgentState
    from app.llm.base import BaseLLMProvider

logger = get_logger(__name__)


class ReportAgent(BaseAgent):
    """Generates a structured engineering assessment report.

    Collects all outputs from upstream agents and passes them to the LLM
    using ReportPrompts.REPORT_TEMPLATE to produce a comprehensive,
    citation-backed engineering report.

    Args:
        llm_provider: Active LLM provider.
    """

    def __init__(self, llm_provider: "BaseLLMProvider") -> None:
        self._llm = llm_provider

    @property
    def name(self) -> str:
        return "ReportAgent"

    async def run(self, state: "AgentState") -> "AgentState":
        """Generate the final structured engineering report.

        Args:
            state: Fully populated AgentState from all upstream agents.

        Returns:
            Updated AgentState with report_text set.
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
        recommendations = state.get("structured_recommendations", [])
        enriched_kg = state.get("enriched_kg_context", "")
        risk_chains = state.get("risk_chains", [])
        defects = state.get("extracted_defects", [])
        components = state.get("extracted_components", [])
        intent = state.get("query_intent", "general")

        try:
            # --- Executive Summary Context ---
            confidence_score = rag_response.confidence.score if rag_response else 0.0
            condition_rating = self._infer_condition_rating(
                recommendations=recommendations,
                confidence=confidence_score,
            )

            exec_summary_parts = [
                f"Query intent: {intent.replace('_', ' ').title()}.",
                f"Overall confidence: {confidence_score:.2f}.",
                f"Inferred building condition rating: {condition_rating}.",
            ]
            if defects:
                exec_summary_parts.append(f"Defects under analysis: {', '.join(defects[:5])}.")
            if components:
                exec_summary_parts.append(f"Structural elements involved: {', '.join(components[:5])}.")
            executive_summary_context = " ".join(exec_summary_parts)

            # --- Defect Details ---
            defect_parts = []
            if rag_response and rag_response.sources:
                for src in rag_response.sources[:4]:
                    defect_parts.append(
                        f"- **{src.document_name}** "
                        + (f"Page {src.page}" if src.page else "")
                        + (f", {src.section}" if src.section else "")
                        + f"\n  > {src.chunk_preview}"
                    )
            defect_details = "\n".join(defect_parts) if defect_parts else "No document-sourced defect details."

            # --- Cause Analysis ---
            cause_parts = []
            if rag_response and rag_response.kg_context:
                for entity in rag_response.kg_context[:4]:
                    causes = [r.target for r in entity.relationships if r.type == "CAUSED_BY"]
                    if causes:
                        cause_parts.append(f"- `{entity.entity}` ← caused by: {', '.join(causes[:3])}")
            if enriched_kg:
                cause_parts.append(enriched_kg[:1000])
            cause_analysis = "\n".join(cause_parts) if cause_parts else "Insufficient context for root cause analysis."

            # --- Recommendations block ---
            rec_parts = []
            for i, rec in enumerate(recommendations[:6], 1):
                ref = f" [{rec.source_reference}]" if rec.source_reference else ""
                rec_parts.append(
                    f"{i}. [{rec.priority.upper()}] {rec.action[:200]}{ref}"
                )
            recommendations_text = "\n".join(rec_parts) if rec_parts else "No structured recommendations generated."

            # --- Risk Assessment ---
            risk_parts = []
            if risk_chains:
                for rc in risk_chains[:5]:
                    d = rc.get("defect", "unknown")
                    r = rc.get("repair_method", "—")
                    stds = ", ".join(rc.get("standards", []))
                    risk_parts.append(
                        f"- Defect: `{d}` | Repair: `{r}`" + (f" | Ref: {stds}" if stds else "")
                    )
            if rag_response and rag_response.related_components:
                for comp in rag_response.related_components[:3]:
                    if comp.related_defects:
                        risk_parts.append(
                            f"- Component `{comp.name}` at risk from: {', '.join(comp.related_defects[:3])}"
                        )
            risk_assessment = "\n".join(risk_parts) if risk_parts else "No specific risk chains identified."

            # --- LLM call ---
            prompt = ReportPrompts.REPORT_TEMPLATE.format(
                executive_summary_context=executive_summary_context,
                defect_details=defect_details,
                cause_analysis=cause_analysis,
                recommendations=recommendations_text,
                risk_assessment=risk_assessment,
            )

            llm_response = await self._llm.generate(
                prompt=prompt,
                system_prompt=ReportPrompts.SYSTEM_PROMPT,
                max_tokens=2000,
            )

            report_text = llm_response.content

            # --- Confidence ---
            sections_populated = sum([
                bool(defects), bool(cause_parts), bool(rec_parts), bool(risk_parts)
            ])
            data_confidence = sections_populated / 4.0
            source_confidence = confidence_score
            confidence = round((data_confidence + source_confidence) / 2.0, 3)

            # --- Reason ---
            high_recs = sum(1 for r in recommendations if r.priority == "high")
            reason = (
                f"Generated {len(report_text.split())} word engineering report. "
                f"Condition rating: '{condition_rating}'. "
                f"{len(recommendations)} recommendation(s) included "
                f"({high_recs} high-priority). "
                f"Report draws from {len(rag_response.sources) if rag_response else 0} "
                f"document source(s) and "
                f"{len(rag_response.kg_context) if rag_response else 0} KG entity context(s)."
            )

            step = AgentExecutionStep(
                agent=self.name,
                status="success",
                time_ms=timer.elapsed_ms(),
                confidence=confidence,
                reason=reason,
            )
            trace.append(step)

            state["report_text"] = report_text

            logger.info(
                "report_agent_complete",
                word_count=len(report_text.split()),
                condition_rating=condition_rating,
                confidence=confidence,
            )

        except Exception as exc:
            logger.error("report_agent_failed", error=str(exc))
            step = AgentExecutionStep(
                agent=self.name,
                status="failed",
                time_ms=timer.elapsed_ms(),
                confidence=0.0,
                reason="ReportAgent failed during LLM report generation.",
                error=str(exc),
            )
            trace.append(step)
            state["report_text"] = "Report generation failed. Please refer to the structured answer above."

        state["execution_trace"] = trace
        return state

    def _infer_condition_rating(self, recommendations: list, confidence: float) -> str:
        """Infer a CPWD-aligned condition rating from recommendation severity and confidence."""
        high_count = sum(1 for r in recommendations if r.priority == "high")
        if high_count >= 3 or confidence < 0.30:
            return "Critical"
        if high_count >= 2 or confidence < 0.50:
            return "Poor"
        if high_count >= 1 or confidence < 0.70:
            return "Fair"
        if confidence >= 0.85:
            return "Good"
        return "Satisfactory"
