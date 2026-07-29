"""Knowledge Graph Reasoning Agent — Phase 6.

Performs multi-hop KG traversal to enrich the context beyond what the
Hybrid RAG pipeline already retrieved. Expands defect → risk → component
chains and surfaces relationships not visible from direct retrieval.

Decision recorded in trace:
    - reason: lists the specific defect/component expansions performed and
              what new relationships were discovered
    - confidence: based on number of enrichment paths found vs. queried

This agent goes BEYOND the single-hop KG context already in rag_response.
It traverses:
    1. Defect → CAUSED_BY → Cause → (multiple paths)
    2. Defect → REPAIRED_BY → RepairMethod → SPECIFIED_IN → BuildingStandard
    3. Component → AFFECTED_BY → Defect → CAUSES → Risk
    4. Risk chains: What risks does the defect create for other components?
"""

from typing import Any, TYPE_CHECKING

from app.agents.base import BaseAgent
from app.agents.state import AgentExecutionStep, AgentTimer
from app.core.logging import get_logger
from app.knowledge_graph.queries import (
    get_defect_subgraph,
    get_component_subgraph,
    get_repair_recommendations_from_kg,
    format_kg_context_for_rag,
)

if TYPE_CHECKING:
    from app.agents.state import AgentState

logger = get_logger(__name__)

_RISK_CHAIN_CYPHER = """
MATCH (d:Defect)-[:CAUSED_BY]->(c:Cause)
WHERE toLower(d.name) CONTAINS $defect_name
OPTIONAL MATCH (d)-[:AFFECTS]->(comp:Component)
OPTIONAL MATCH (r:Risk)-[:ASSOCIATED_WITH]->(d)
RETURN d.name AS defect,
       collect(DISTINCT c.name) AS causes,
       collect(DISTINCT comp.name) AS components,
       collect(DISTINCT r.name) AS risks
LIMIT 5
"""


class KGReasoningAgent(BaseAgent):
    """Enriches engineering context through multi-hop Knowledge Graph traversal.

    After the RetrievalAgent fetches primary KG context, this agent goes deeper:
    - Expands each extracted defect to its full cause → repair → standard chain
    - Surfaces risk chains that reveal downstream consequences
    - Enriches component context with all associated defects and materials

    Args:
        None — uses module-level Neo4j query functions (existing app/knowledge_graph/)
    """

    @property
    def name(self) -> str:
        return "KGReasoningAgent"

    async def run(self, state: "AgentState") -> "AgentState":
        """Run multi-hop KG reasoning and store enriched context in state.

        Args:
            state: AgentState with extracted_defects and extracted_components populated.

        Returns:
            Updated AgentState with enriched_kg_context and risk_chains set.
        """
        timer = AgentTimer()
        timer.start()

        trace = list(state.get("execution_trace", []))

        # Skip conditions
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

        if not state.get("include_kg", True):
            step = AgentExecutionStep(
                agent=self.name,
                status="skipped",
                time_ms=timer.elapsed_ms(),
                confidence=0.0,
                reason="Skipped: KG reasoning disabled by caller (include_kg=False).",
            )
            trace.append(step)
            state["execution_trace"] = trace
            return state

        defects = state.get("extracted_defects", [])
        components = state.get("extracted_components", [])

        if not defects and not components:
            step = AgentExecutionStep(
                agent=self.name,
                status="skipped",
                time_ms=timer.elapsed_ms(),
                confidence=0.0,
                reason=(
                    "Skipped: No defects or components were extracted from the query. "
                    "KG reasoning requires at least one entity to expand."
                ),
            )
            trace.append(step)
            state["execution_trace"] = trace
            return state

        # Track what was expanded
        expanded_defects: list[str] = []
        expanded_components: list[str] = []
        new_relationships: list[str] = []
        risk_chains: list[dict[str, Any]] = []
        all_subgraphs: list[dict[str, Any]] = []

        try:
            # --- Defect expansion ---
            for defect in defects[:4]:
                try:
                    sg = await get_defect_subgraph(defect)
                    if sg and sg.get("defects_found"):
                        all_subgraphs.append(sg)
                        expanded_defects.append(defect)
                        for d_data in sg["defects_found"]:
                            causes = d_data.get("causes", [])
                            repairs = [r.get("repair") for r in d_data.get("repairs", []) if r.get("repair")]
                            affected = d_data.get("affected_components", [])
                            if causes:
                                new_relationships.append(
                                    f"'{defect}' caused by: {', '.join(causes[:3])}"
                                )
                            if repairs:
                                new_relationships.append(
                                    f"'{defect}' repaired by: {', '.join(repairs[:2])}"
                                )
                            if affected:
                                new_relationships.append(
                                    f"'{defect}' affects: {', '.join(affected[:3])}"
                                )

                    # Repair recommendations with standards
                    recs = await get_repair_recommendations_from_kg(defect)
                    if recs:
                        risk_chains.extend(recs[:3])

                except Exception as exc:
                    logger.debug("kg_defect_expansion_failed", defect=defect, error=str(exc))

            # --- Component expansion ---
            for component in components[:3]:
                try:
                    sg = await get_component_subgraph(component)
                    if sg and sg.get("components_found"):
                        all_subgraphs.append(sg)
                        expanded_components.append(component)
                        for c_data in sg["components_found"]:
                            def_list = c_data.get("affecting_defects", [])
                            mat_list = c_data.get("materials", [])
                            if def_list:
                                new_relationships.append(
                                    f"'{component}' affected by: {', '.join(def_list[:3])}"
                                )
                            if mat_list:
                                new_relationships.append(
                                    f"'{component}' made of: {', '.join(mat_list[:2])}"
                                )
                except Exception as exc:
                    logger.debug("kg_component_expansion_failed", component=component, error=str(exc))

            # --- Format enriched context ---
            enriched_parts: list[str] = ["### Enriched Knowledge Graph Context (Multi-Hop Reasoning)\n"]

            if new_relationships:
                enriched_parts.append("**Expanded Relationships Discovered:**")
                for rel in new_relationships[:12]:
                    enriched_parts.append(f"- {rel}")
                enriched_parts.append("")

            if all_subgraphs:
                enriched_parts.append(format_kg_context_for_rag(all_subgraphs[0]))

            enriched_context = "\n".join(enriched_parts)

            # --- Confidence: based on how many defects/components were successfully expanded ---
            total_queried = len(defects[:4]) + len(components[:3])
            total_expanded = len(expanded_defects) + len(expanded_components)
            confidence = round(total_expanded / max(1, total_queried), 3) if total_queried > 0 else 0.0

            # --- Reason summary ---
            reason_parts = []
            if expanded_defects:
                reason_parts.append(
                    f"Expanded defect(s) '{', '.join(expanded_defects)}' to "
                    f"related causes, repair methods, and affected components."
                )
            if expanded_components:
                reason_parts.append(
                    f"Expanded component(s) '{', '.join(expanded_components)}' to "
                    f"associated defects and materials."
                )
            if new_relationships:
                reason_parts.append(
                    f"Discovered {len(new_relationships)} new relationship(s) through multi-hop traversal."
                )
            if risk_chains:
                reason_parts.append(
                    f"Found {len(risk_chains)} repair recommendation(s) with standard references."
                )
            if not reason_parts:
                reason_parts.append(
                    "KG traversal completed but found no new relationships beyond primary retrieval."
                )

            reason = " ".join(reason_parts)

            step = AgentExecutionStep(
                agent=self.name,
                status="success",
                time_ms=timer.elapsed_ms(),
                confidence=confidence,
                reason=reason,
            )
            trace.append(step)

            state["enriched_kg_context"] = enriched_context
            state["risk_chains"] = risk_chains

            logger.info(
                "kg_reasoning_agent_complete",
                expanded_defects=expanded_defects,
                expanded_components=expanded_components,
                relationships=len(new_relationships),
                confidence=confidence,
            )

        except Exception as exc:
            logger.error("kg_reasoning_agent_failed", error=str(exc))
            step = AgentExecutionStep(
                agent=self.name,
                status="failed",
                time_ms=timer.elapsed_ms(),
                confidence=0.0,
                reason="KGReasoningAgent encountered an unexpected error during graph traversal.",
                error=str(exc),
            )
            trace.append(step)
            state["enriched_kg_context"] = ""
            state["risk_chains"] = []

        state["execution_trace"] = trace
        return state
