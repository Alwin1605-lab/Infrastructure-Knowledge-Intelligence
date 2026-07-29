"""Query Analysis Agent — Phase 6.

Classifies user intent, validates domain, extracts building entities,
and reformulates the query for optimal retrieval.

Decision recorded in trace:
    - reason: summarizes extracted defects, components, and intent class
    - confidence: based on entity extraction richness and domain clarity

Intent classes:
    - defect_diagnosis      : User asks why a defect occurs
    - repair_recommendation : User asks how to repair a defect
    - inspection_protocol   : User asks how to inspect a component
    - maintenance_planning  : User asks for a maintenance schedule or plan
    - standards_lookup      : User asks about code/standard clauses
    - general               : Catch-all for valid building queries

Fallback: If LLM call fails, uses existing QueryProcessor (Phase 5) for entity
          extraction and assigns "general" intent with medium confidence.
"""

import re
import json
from typing import TYPE_CHECKING

from app.agents.base import BaseAgent
from app.agents.state import AgentExecutionStep, AgentTimer
from app.core.logging import get_logger
from app.rag.query_processor import QueryProcessor, BUILDING_DEFECTS, BUILDING_COMPONENTS

if TYPE_CHECKING:
    from app.agents.state import AgentState
    from app.llm.base import BaseLLMProvider

logger = get_logger(__name__)

# Intent classification keyword map (regex-based fast path before LLM)
_INTENT_PATTERNS: list[tuple[str, str]] = [
    (r"\b(cause[sd]?|why|reason|origin|result[s]? in|leads? to)\b", "defect_diagnosis"),
    (r"\b(repair|fix|treat|remedy|rehabilitat|retrofit|strengthen|seal|inject)\b", "repair_recommendation"),
    (r"\b(inspect|inspection|check|survey|assess|test|evaluate|measure|detect)\b", "inspection_protocol"),
    (r"\b(maintain|maintenance|schedule|preventive|periodic|routine|plan)\b", "maintenance_planning"),
    (r"\b(standard|code|clause|IS\s*\d+|NBC|CPWD|BIS|specification|provision)\b", "standards_lookup"),
]

_INTENT_PROMPT = (
    "You are an intent classifier for a building engineering Q&A system. "
    "Classify the user query into exactly ONE of these intents:\n"
    "- defect_diagnosis: asking why a building defect occurs\n"
    "- repair_recommendation: asking how to repair or treat a defect\n"
    "- inspection_protocol: asking how to inspect or assess a building element\n"
    "- maintenance_planning: asking for maintenance schedules or plans\n"
    "- standards_lookup: asking about building codes or standards\n"
    "- general: valid building question that doesn't fit the above\n\n"
    "Reply with ONLY a JSON object: "
    '{{"intent": "<one of the above>", "confidence": <float 0.0-1.0>}}\n\n'
    "Query: {question}"
)


class QueryAnalysisAgent(BaseAgent):
    """Analyzes user queries for intent, domain validity, and entity extraction.

    Combines a fast regex pass (existing QueryProcessor) with an LLM intent
    classification call for richer classification. Falls back to regex-only
    if the LLM call fails.

    Args:
        llm_provider: Active LLM provider for intent classification.
    """

    def __init__(self, llm_provider: "BaseLLMProvider") -> None:
        self._llm = llm_provider
        self._processor = QueryProcessor()

    @property
    def name(self) -> str:
        return "QueryAnalysisAgent"

    async def run(self, state: "AgentState") -> "AgentState":
        """Run query analysis and update state with intent, entities, and reformulated query.

        Args:
            state: Current AgentState with original_question populated.

        Returns:
            Updated AgentState with query_intent, extracted_*, reformulated_query,
            is_building_domain, and a trace step appended.
        """
        timer = AgentTimer()
        timer.start()

        question = state.get("original_question", "")
        trace = list(state.get("execution_trace", []))

        try:
            # --- Step 1: Domain guard + entity extraction (existing Phase 5) ---
            processed = self._processor.preprocess(question)

            if not processed.is_building_domain:
                step = AgentExecutionStep(
                    agent=self.name,
                    status="success",
                    time_ms=timer.elapsed_ms(),
                    confidence=0.99,
                    reason=(
                        f"Domain validation failed. Query matched a non-building exclusion pattern. "
                        f"Rejection reason: {processed.rejection_reason}"
                    ),
                )
                trace.append(step)
                state["is_building_domain"] = False
                state["rejection_reason"] = processed.rejection_reason
                state["execution_trace"] = trace
                return state

            # --- Step 2: LLM intent classification ---
            intent = self._classify_intent_fast(question)
            llm_confidence = 0.75  # default for fast-path

            try:
                prompt = _INTENT_PROMPT.format(question=question)
                response = await self._llm.generate(prompt=prompt, max_tokens=80, temperature=0.0)
                raw = response.content.strip()
                # Extract JSON from response
                json_match = re.search(r'\{.*?\}', raw, re.S)
                if json_match:
                    parsed = json.loads(json_match.group())
                    intent = parsed.get("intent", intent)
                    llm_confidence = float(parsed.get("confidence", 0.75))
                    # Validate intent value
                    valid_intents = {"defect_diagnosis", "repair_recommendation",
                                     "inspection_protocol", "maintenance_planning",
                                     "standards_lookup", "general"}
                    if intent not in valid_intents:
                        intent = "general"
            except Exception as exc:
                logger.debug("intent_llm_fallback", error=str(exc), intent=intent)
                # Keep regex-based intent, lower confidence
                llm_confidence = 0.65

            # --- Step 3: Build reason summary ---
            defects = processed.extracted_defects
            components = processed.extracted_components
            repairs = processed.extracted_repair_methods

            reason_parts = [f"Intent classified as '{intent}'."]
            if defects:
                reason_parts.append(f"Defects detected: {', '.join(defects[:3])}.")
            if components:
                reason_parts.append(f"Components detected: {', '.join(components[:3])}.")
            if repairs:
                reason_parts.append(f"Repair methods detected: {', '.join(repairs[:2])}.")
            if not defects and not components:
                reason_parts.append("No specific building entities extracted; using general retrieval.")

            reason = " ".join(reason_parts)

            # --- Step 4: Confidence —  higher if entities found + LLM confirmed ---
            entity_bonus = min(0.15, (len(defects) + len(components)) * 0.05)
            confidence = round(min(1.0, llm_confidence + entity_bonus), 3)

            step = AgentExecutionStep(
                agent=self.name,
                status="success",
                time_ms=timer.elapsed_ms(),
                confidence=confidence,
                reason=reason,
            )
            trace.append(step)

            state["is_building_domain"] = True
            state["rejection_reason"] = None
            state["query_intent"] = intent
            state["extracted_defects"] = processed.extracted_defects
            state["extracted_components"] = processed.extracted_components
            state["extracted_repair_methods"] = processed.extracted_repair_methods
            state["reformulated_query"] = processed.expanded_query
            state["execution_trace"] = trace

            logger.info(
                "query_analysis_complete",
                intent=intent,
                defects=defects,
                components=components,
                confidence=confidence,
            )

        except Exception as exc:
            logger.error("query_analysis_agent_failed", error=str(exc))
            step = AgentExecutionStep(
                agent=self.name,
                status="failed",
                time_ms=timer.elapsed_ms(),
                confidence=0.0,
                reason="QueryAnalysisAgent encountered an unexpected error.",
                error=str(exc),
            )
            trace.append(step)
            state["execution_trace"] = trace
            state["reformulated_query"] = question

        return state

    def _classify_intent_fast(self, question: str) -> str:
        """Classify intent using regex patterns (fast path, no LLM)."""
        q_lower = question.lower()
        for pattern, intent in _INTENT_PATTERNS:
            if re.search(pattern, q_lower):
                return intent
        return "general"
