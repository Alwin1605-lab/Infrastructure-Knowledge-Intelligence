"""Comprehensive tests for Phase 6 — Agentic AI Pipeline.

Tests cover:
    1. AgentState — creation, timer, execution step serialization
    2. QueryAnalysisAgent — intent classification, domain rejection, entity extraction,
                            reason/confidence fields
    3. RetrievalAgent — delegation to RAG pipeline, skipping on domain rejection,
                        reason/confidence population
    4. KGReasoningAgent — multi-hop traversal, entity-based skipping, KG failure survival
    5. RecommendationAgent — recommendation parsing, priority classification, fallback
    6. ReportAgent — report generation, condition rating, skipping on rejection
    7. AgentOrchestrator — full pipeline with mocks, domain rejection routing,
                           retry on failure, overall_confidence computation
    8. Schema validation — AgentPipelineResponse field completeness
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.state import AgentExecutionStep, AgentState, AgentTimer, new_agent_state
from app.schemas.chat import (
    ChatResponse,
    ChatRequest,
    ConfidenceScore,
    EngineeringRecommendation,
    KGEntityContext,
    KGRelationship,
    RelatedComponent,
    ResponseTime,
    SourceDocument,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_chat_response(
    confidence_score: float = 0.85,
    grounding: str = "rag_and_kg",
    num_sources: int = 2,
) -> ChatResponse:
    """Build a minimal ChatResponse for injection into agent state."""
    sources = [
        SourceDocument(
            document_name=f"CPWD_Manual_Volume_{i}.pdf",
            page=10 + i,
            section="4.3 Spalling",
            chunk_preview="Spalling occurs due to corrosion of embedded reinforcement.",
            relevance_score=0.85,
        )
        for i in range(num_sources)
    ]
    kg_context = [
        KGEntityContext(
            entity="spalling",
            type="Defect",
            relationships=[
                KGRelationship(type="CAUSED_BY", target="corrosion", target_type="Cause"),
                KGRelationship(type="REPAIRED_BY", target="concrete jacketing", target_type="RepairMethod"),
            ],
        )
    ]
    return ChatResponse(
        answer="Spalling in RCC columns is primarily caused by corrosion of embedded steel reinforcement.",
        sources=sources,
        kg_context=kg_context,
        confidence=ConfidenceScore(
            score=confidence_score,
            level="high" if confidence_score >= 0.75 else "medium",
            grounding=grounding,
            reasoning=f"Grounded in {num_sources} document sources and KG.",
        ),
        recommendations=[
            EngineeringRecommendation(
                action="Conduct half-cell potential test on affected columns.",
                priority="high",
                category="investigation",
                source_reference="CPWD Handbook Section 4.1",
            )
        ],
        related_components=[
            RelatedComponent(
                name="RCC Column",
                type="Structural Element",
                related_defects=["spalling", "corrosion"],
                related_materials=["reinforced concrete"],
                connection="Primary load-bearing element affected",
            )
        ],
        response_time=ResponseTime(
            total_ms=1500.0,
            retrieval_ms=200.0,
            kg_lookup_ms=80.0,
            llm_generation_ms=1100.0,
            post_processing_ms=120.0,
        ),
    )


# ===========================================================================
# 1. AgentState Tests
# ===========================================================================

class TestAgentState:

    def test_new_agent_state_has_all_required_fields(self):
        """new_agent_state() must populate all mandatory fields."""
        state = new_agent_state("What causes spalling?", top_k=5, include_kg=True)
        assert state["original_question"] == "What causes spalling?"
        assert state["top_k"] == 5
        assert state["include_kg"] is True
        assert isinstance(state["session_id"], str)
        assert len(state["session_id"]) == 36  # UUID format
        assert state["execution_trace"] == []

    def test_new_agent_state_is_independent(self):
        """Each call to new_agent_state() produces a distinct session_id."""
        s1 = new_agent_state("Q1")
        s2 = new_agent_state("Q2")
        assert s1["session_id"] != s2["session_id"]

    def test_agent_execution_step_to_dict(self):
        """AgentExecutionStep.to_dict() must include all fields including reason and confidence."""
        step = AgentExecutionStep(
            agent="KGReasoningAgent",
            status="success",
            time_ms=38.2,
            confidence=0.87,
            reason="Expanded defect 'spalling' to corrosion and exposed reinforcement.",
        )
        d = step.to_dict()
        assert d["agent"] == "KGReasoningAgent"
        assert d["status"] == "success"
        assert d["confidence"] == 0.87
        assert "spalling" in d["reason"]
        assert "error" not in d  # error field omitted when None

    def test_agent_execution_step_includes_error(self):
        """Failed step must include error field in to_dict()."""
        step = AgentExecutionStep(
            agent="RetrievalAgent",
            status="failed",
            time_ms=5.0,
            confidence=0.0,
            reason="Agent failed.",
            error="Connection refused",
        )
        d = step.to_dict()
        assert d["error"] == "Connection refused"

    def test_agent_timer_measures_elapsed(self):
        """AgentTimer.elapsed_ms() must return a positive non-zero value."""
        import time
        timer = AgentTimer()
        timer.start()
        time.sleep(0.01)  # 10ms sleep
        elapsed = timer.elapsed_ms()
        assert elapsed >= 5.0  # at least 5ms
        assert elapsed < 1000.0  # less than 1s


# ===========================================================================
# 2. QueryAnalysisAgent Tests
# ===========================================================================

class TestQueryAnalysisAgent:

    def _make_agent(self, llm_response_text: str = '{"intent": "defect_diagnosis", "confidence": 0.93}'):
        from app.agents.query_analysis_agent import QueryAnalysisAgent
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value=MagicMock(content=llm_response_text))
        return QueryAnalysisAgent(llm_provider=mock_llm)

    @pytest.mark.asyncio
    async def test_domain_rejection_recorded_in_trace(self):
        """Highway bridge query must be rejected and trace must record reason."""
        agent = self._make_agent()
        state = new_agent_state("How do you inspect a highway bridge for corrosion?")
        state = await agent.run(state)

        assert state["is_building_domain"] is False
        assert len(state["execution_trace"]) == 1
        step = state["execution_trace"][0]
        assert step.status == "success"
        assert step.confidence > 0.90
        assert "non-building" in step.reason.lower() or "domain" in step.reason.lower()

    @pytest.mark.asyncio
    async def test_building_query_extracts_defects(self):
        """Spalling query must extract defect and component entities."""
        agent = self._make_agent()
        state = new_agent_state("What causes spalling in an RCC column?")
        state = await agent.run(state)

        assert state["is_building_domain"] is True
        assert "spalling" in state["extracted_defects"]
        assert "column" in state["extracted_components"]

    @pytest.mark.asyncio
    async def test_intent_in_trace_reason(self):
        """Trace reason must mention the classified intent."""
        agent = self._make_agent('{"intent": "repair_recommendation", "confidence": 0.88}')
        state = new_agent_state("How should spalling in beams be repaired?")
        state = await agent.run(state)

        assert len(state["execution_trace"]) == 1
        step = state["execution_trace"][0]
        assert "repair_recommendation" in step.reason

    @pytest.mark.asyncio
    async def test_confidence_increases_with_entities(self):
        """Agent confidence must be higher when multiple entities are extracted."""
        agent_rich = self._make_agent('{"intent": "defect_diagnosis", "confidence": 0.80}')
        state_rich = new_agent_state("What causes spalling and corrosion in columns and slabs?")
        state_rich = await agent_rich.run(state_rich)

        agent_poor = self._make_agent('{"intent": "general", "confidence": 0.60}')
        state_poor = new_agent_state("Tell me about buildings.")
        state_poor = await agent_poor.run(state_poor)

        rich_confidence = state_rich["execution_trace"][0].confidence
        poor_confidence = state_poor["execution_trace"][0].confidence
        assert rich_confidence >= poor_confidence

    @pytest.mark.asyncio
    async def test_llm_failure_falls_back_gracefully(self):
        """If LLM raises, agent must still succeed using regex fallback."""
        from app.agents.query_analysis_agent import QueryAnalysisAgent
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(side_effect=Exception("LLM unavailable"))
        agent = QueryAnalysisAgent(llm_provider=mock_llm)

        state = new_agent_state("What causes crack in a beam?")
        state = await agent.run(state)

        # Must still succeed with regex-based intent
        assert state["is_building_domain"] is True
        assert len(state["execution_trace"]) == 1
        assert state["execution_trace"][0].status == "success"


# ===========================================================================
# 3. RetrievalAgent Tests
# ===========================================================================

class TestRetrievalAgent:

    def _make_agent(self, rag_response=None):
        from app.agents.retrieval_agent import RetrievalAgent
        mock_pipeline = MagicMock()
        if rag_response is None:
            rag_response = _make_chat_response()
        mock_pipeline.query = AsyncMock(return_value=rag_response)
        return RetrievalAgent(rag_pipeline=mock_pipeline)

    @pytest.mark.asyncio
    async def test_stores_rag_response_in_state(self):
        """RetrievalAgent must store ChatResponse in state['rag_response']."""
        agent = self._make_agent()
        state = new_agent_state("What causes spalling?")
        state["reformulated_query"] = "spalling RCC column corrosion"
        state = await agent.run(state)

        assert state["rag_response"] is not None
        assert state["rag_response"].answer

    @pytest.mark.asyncio
    async def test_skipped_on_domain_rejection(self):
        """RetrievalAgent must skip if is_building_domain is False."""
        from app.agents.retrieval_agent import RetrievalAgent
        mock_pipeline = MagicMock()
        mock_pipeline.query = AsyncMock()
        agent = RetrievalAgent(rag_pipeline=mock_pipeline)

        state = new_agent_state("How do I design a highway?")
        state["is_building_domain"] = False
        state = await agent.run(state)

        assert len(state["execution_trace"]) == 1
        assert state["execution_trace"][0].status == "skipped"
        mock_pipeline.query.assert_not_called()

    @pytest.mark.asyncio
    async def test_trace_reason_includes_source_count(self):
        """Trace reason must mention number of retrieved sources."""
        agent = self._make_agent(_make_chat_response(num_sources=3))
        state = new_agent_state("What causes spalling?")
        state["reformulated_query"] = "spalling column"
        state = await agent.run(state)

        step = state["execution_trace"][0]
        assert step.status == "success"
        assert "3" in step.reason  # 3 source chunks
        assert step.confidence > 0.0

    @pytest.mark.asyncio
    async def test_confidence_matches_rag_confidence(self):
        """RetrievalAgent confidence must reflect the RAG pipeline confidence score."""
        agent = self._make_agent(_make_chat_response(confidence_score=0.92))
        state = new_agent_state("Spalling causes?")
        state["reformulated_query"] = "spalling"
        state = await agent.run(state)

        step = state["execution_trace"][0]
        assert abs(step.confidence - 0.92) < 0.01


# ===========================================================================
# 4. KGReasoningAgent Tests
# ===========================================================================

class TestKGReasoningAgent:

    @pytest.mark.asyncio
    async def test_skipped_with_no_entities(self):
        """KGReasoningAgent must skip if no defects or components were extracted."""
        from app.agents.kg_reasoning_agent import KGReasoningAgent
        agent = KGReasoningAgent()
        state = new_agent_state("Tell me about buildings.")
        state["extracted_defects"] = []
        state["extracted_components"] = []
        state = await agent.run(state)

        step = state["execution_trace"][0]
        assert step.status == "skipped"
        assert "no defects" in step.reason.lower() or "no entity" in step.reason.lower()

    @pytest.mark.asyncio
    async def test_skipped_when_include_kg_false(self):
        """KGReasoningAgent must skip if include_kg is False."""
        from app.agents.kg_reasoning_agent import KGReasoningAgent
        agent = KGReasoningAgent()
        state = new_agent_state("Spalling?", include_kg=False)
        state["extracted_defects"] = ["spalling"]
        state["include_kg"] = False
        state = await agent.run(state)

        assert state["execution_trace"][0].status == "skipped"

    @pytest.mark.asyncio
    async def test_expands_defects_with_mock_kg(self):
        """KGReasoningAgent must record expanded relationships in reason."""
        from app.agents.kg_reasoning_agent import KGReasoningAgent
        agent = KGReasoningAgent()

        state = new_agent_state("What causes spalling in columns?")
        state["extracted_defects"] = ["spalling"]
        state["extracted_components"] = ["column"]
        state["include_kg"] = True

        with patch("app.agents.kg_reasoning_agent.get_defect_subgraph", new_callable=AsyncMock) as mock_defect, \
             patch("app.agents.kg_reasoning_agent.get_component_subgraph", new_callable=AsyncMock) as mock_comp, \
             patch("app.agents.kg_reasoning_agent.get_repair_recommendations_from_kg", new_callable=AsyncMock) as mock_rec:

            mock_defect.return_value = {
                "defects_found": [{
                    "defect": "spalling",
                    "causes": ["corrosion", "carbonation"],
                    "repairs": [{"repair": "concrete jacketing", "standard": "IS 456"}],
                    "affected_components": ["column", "beam"],
                }]
            }
            mock_comp.return_value = {
                "components_found": [{
                    "component": "column",
                    "affecting_defects": ["spalling", "corrosion"],
                    "materials": ["reinforced concrete"],
                    "part_of": ["frame"],
                }]
            }
            mock_rec.return_value = [
                {"defect": "spalling", "repair_method": "concrete jacketing", "standards": ["IS 456"]}
            ]

            state = await agent.run(state)

        step = state["execution_trace"][0]
        assert step.status == "success"
        assert step.confidence > 0.0
        assert "spalling" in step.reason.lower()
        assert state["enriched_kg_context"] != ""

    @pytest.mark.asyncio
    async def test_survives_kg_connection_failure(self):
        """KGReasoningAgent must record failure but not raise."""
        from app.agents.kg_reasoning_agent import KGReasoningAgent
        agent = KGReasoningAgent()

        state = new_agent_state("Spalling?")
        state["extracted_defects"] = ["spalling"]
        state["extracted_components"] = []

        with patch("app.agents.kg_reasoning_agent.get_defect_subgraph", new_callable=AsyncMock) as mock_defect, \
             patch("app.agents.kg_reasoning_agent.get_repair_recommendations_from_kg", new_callable=AsyncMock) as mock_rec:
            mock_defect.side_effect = Exception("Neo4j connection refused")
            mock_rec.return_value = []

            # Must not raise
            state = await agent.run(state)

        # Step should still be recorded (success with 0 entities, or failed gracefully)
        assert len(state["execution_trace"]) == 1


# ===========================================================================
# 5. RecommendationAgent Tests
# ===========================================================================

class TestRecommendationAgent:

    def _make_agent(self, llm_text: str):
        from app.agents.recommendation_agent import RecommendationAgent
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value=MagicMock(content=llm_text))
        return RecommendationAgent(llm_provider=mock_llm)

    @pytest.mark.asyncio
    async def test_generates_recommendations_from_llm(self):
        """RecommendationAgent must parse LLM bullet list into EngineeringRecommendation objects."""
        llm_text = (
            "1. Conduct half-cell potential test on columns urgently to assess corrosion extent. "
            "[CPWD Handbook Section 4.1]\n"
            "2. Apply epoxy injection to seal active cracks immediately.\n"
            "3. Consider long-term monitoring with crack gauges.\n"
        )
        agent = self._make_agent(llm_text)
        state = new_agent_state("Repair spalling columns?")
        state["extracted_defects"] = ["spalling"]
        state["extracted_components"] = ["column"]
        state["rag_response"] = _make_chat_response()
        state["enriched_kg_context"] = ""
        state["risk_chains"] = []

        state = await agent.run(state)

        assert len(state["structured_recommendations"]) >= 1
        step = state["execution_trace"][0]
        assert step.status == "success"
        assert step.confidence > 0.0
        assert "spalling" in step.reason.lower()

    @pytest.mark.asyncio
    async def test_priority_classification(self):
        """High-priority keywords must produce high-priority recommendations."""
        llm_text = "1. Immediately remove critically damaged column cladding for safety.\n"
        agent = self._make_agent(llm_text)
        state = new_agent_state("Repair columns?")
        state["rag_response"] = _make_chat_response(confidence_score=0.88)
        state["enriched_kg_context"] = ""
        state["risk_chains"] = []
        state["extracted_defects"] = ["spalling"]
        state["extracted_components"] = ["column"]

        state = await agent.run(state)

        recs = state["structured_recommendations"]
        assert any(r.priority == "high" for r in recs)

    @pytest.mark.asyncio
    async def test_reason_reports_priority_counts(self):
        """Trace reason must report counts of high/medium/low priority recommendations."""
        llm_text = (
            "1. Urgent: seal cracks immediately.\n"
            "2. Monitor crack widths periodically.\n"
            "3. Consider structural audit in future.\n"
        )
        agent = self._make_agent(llm_text)
        state = new_agent_state("Repair?")
        state["rag_response"] = _make_chat_response()
        state["enriched_kg_context"] = ""
        state["risk_chains"] = []
        state["extracted_defects"] = ["crack"]
        state["extracted_components"] = []

        state = await agent.run(state)

        step = state["execution_trace"][0]
        assert "high-priority" in step.reason.lower() or "recommendation" in step.reason.lower()


# ===========================================================================
# 6. ReportAgent Tests
# ===========================================================================

class TestReportAgent:

    def _make_agent(self, llm_text: str = "## Executive Summary\n\nBuilding is in Fair condition..."):
        from app.agents.report_agent import ReportAgent
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value=MagicMock(content=llm_text))
        return ReportAgent(llm_provider=mock_llm)

    @pytest.mark.asyncio
    async def test_generates_report_text(self):
        """ReportAgent must populate state['report_text'] with non-empty text."""
        agent = self._make_agent("## Executive Summary\n\nBuilding condition: Fair.\n\n## Risk Matrix\n\nHigh risk.")
        state = new_agent_state("Spalling in columns?")
        state["rag_response"] = _make_chat_response()
        state["structured_recommendations"] = [
            EngineeringRecommendation(
                action="Conduct half-cell potential test.",
                priority="high",
                category="investigation",
            )
        ]
        state["enriched_kg_context"] = "Expanded: spalling → corrosion"
        state["risk_chains"] = []
        state["extracted_defects"] = ["spalling"]
        state["extracted_components"] = ["column"]
        state["query_intent"] = "defect_diagnosis"

        state = await agent.run(state)

        assert len(state["report_text"]) > 20
        step = state["execution_trace"][0]
        assert step.status == "success"
        assert step.confidence > 0.0
        assert "report" in step.reason.lower()

    @pytest.mark.asyncio
    async def test_condition_rating_critical_with_many_high_recs(self):
        """_infer_condition_rating must return 'Critical' for 3+ high-priority recommendations."""
        from app.agents.report_agent import ReportAgent
        agent = ReportAgent(llm_provider=MagicMock())
        recs = [
            EngineeringRecommendation(action=f"Urgent action {i}", priority="high", category="repair")
            for i in range(3)
        ]
        rating = agent._infer_condition_rating(recs, confidence=0.85)
        assert rating == "Critical"

    @pytest.mark.asyncio
    async def test_condition_rating_good_with_high_confidence(self):
        """_infer_condition_rating must return 'Good' for high confidence and no high-priority recommendations."""
        from app.agents.report_agent import ReportAgent
        agent = ReportAgent(llm_provider=MagicMock())
        recs = [
            EngineeringRecommendation(action="Low priority action", priority="low", category="monitoring")
        ]
        rating = agent._infer_condition_rating(recs, confidence=0.92)
        assert rating == "Good"

    @pytest.mark.asyncio
    async def test_skipped_on_domain_rejection(self):
        """ReportAgent must skip if domain was rejected."""
        agent = self._make_agent()
        state = new_agent_state("Highway bridge?")
        state["is_building_domain"] = False
        state = await agent.run(state)

        assert state["execution_trace"][0].status == "skipped"


# ===========================================================================
# 7. AgentOrchestrator Integration Tests
# ===========================================================================

class TestAgentOrchestrator:

    def _make_orchestrator(self, rag_response=None):
        from app.agents.orchestrator import AgentOrchestrator
        mock_llm = MagicMock()
        mock_llm.provider_name = "groq"
        # Intent LLM call
        mock_llm.generate = AsyncMock(return_value=MagicMock(
            content='{"intent": "defect_diagnosis", "confidence": 0.90}'
        ))

        mock_pipeline = MagicMock()
        if rag_response is None:
            rag_response = _make_chat_response()
        mock_pipeline.query = AsyncMock(return_value=rag_response)

        return AgentOrchestrator(llm_provider=mock_llm, rag_pipeline=mock_pipeline)

    @pytest.mark.asyncio
    async def test_full_pipeline_returns_required_fields(self):
        """Full pipeline must return all required AgentPipelineResponse fields."""
        orchestrator = self._make_orchestrator()

        with patch("app.agents.kg_reasoning_agent.get_defect_subgraph", new_callable=AsyncMock) as mock_defect, \
             patch("app.agents.kg_reasoning_agent.get_component_subgraph", new_callable=AsyncMock) as mock_comp, \
             patch("app.agents.kg_reasoning_agent.get_repair_recommendations_from_kg", new_callable=AsyncMock) as mock_rec:
            mock_defect.return_value = {}
            mock_comp.return_value = {}
            mock_rec.return_value = []

            result = await orchestrator.run(
                question="What causes spalling in RCC columns?",
                top_k=5,
                include_kg=True,
            )

        assert "session_id" in result
        assert "execution_trace" in result
        assert "total_agents_run" in result
        assert "total_pipeline_ms" in result
        assert "overall_confidence" in result
        assert "pipeline_version" in result
        assert result["pipeline_version"] == "6.0"

    @pytest.mark.asyncio
    async def test_domain_rejection_skips_all_downstream(self):
        """Non-building query must skip retrieval, KG, recommendation, and report agents."""
        orchestrator = self._make_orchestrator()

        result = await orchestrator.run(
            question="How do you design a highway bridge for seismic loads?",
            top_k=5,
            include_kg=True,
        )

        assert result["domain_valid"] is False
        assert result["total_agents_run"] == 1  # Only QueryAnalysisAgent ran
        # All downstream steps should be "skipped"
        skipped = [s for s in result["execution_trace"] if s["status"] == "skipped"]
        assert len(skipped) >= 4

    @pytest.mark.asyncio
    async def test_execution_trace_has_reason_and_confidence_for_each_step(self):
        """Every trace step must have non-empty reason and valid confidence."""
        orchestrator = self._make_orchestrator()

        with patch("app.agents.kg_reasoning_agent.get_defect_subgraph", new_callable=AsyncMock) as mock_defect, \
             patch("app.agents.kg_reasoning_agent.get_component_subgraph", new_callable=AsyncMock) as mock_comp, \
             patch("app.agents.kg_reasoning_agent.get_repair_recommendations_from_kg", new_callable=AsyncMock) as mock_rec:
            mock_defect.return_value = {}
            mock_comp.return_value = {}
            mock_rec.return_value = []

            result = await orchestrator.run(
                question="What causes spalling in RCC columns?",
                top_k=5,
                include_kg=True,
            )

        for step in result["execution_trace"]:
            assert "reason" in step, f"Missing reason in step: {step['agent']}"
            assert len(step["reason"]) > 5, f"Reason too short: {step['agent']}"
            assert "confidence" in step, f"Missing confidence in step: {step['agent']}"
            assert 0.0 <= step["confidence"] <= 1.0, f"Invalid confidence: {step['agent']}"

    @pytest.mark.asyncio
    async def test_overall_confidence_is_average_of_successful_steps(self):
        """overall_confidence must be the average of successful agent confidence scores."""
        orchestrator = self._make_orchestrator()

        with patch("app.agents.kg_reasoning_agent.get_defect_subgraph", new_callable=AsyncMock) as mock_defect, \
             patch("app.agents.kg_reasoning_agent.get_component_subgraph", new_callable=AsyncMock) as mock_comp, \
             patch("app.agents.kg_reasoning_agent.get_repair_recommendations_from_kg", new_callable=AsyncMock) as mock_rec:
            mock_defect.return_value = {}
            mock_comp.return_value = {}
            mock_rec.return_value = []

            result = await orchestrator.run(
                question="What causes spalling?",
                top_k=5,
            )

        successful = [s for s in result["execution_trace"] if s["status"] == "success"]
        if successful:
            expected_avg = sum(s["confidence"] for s in successful) / len(successful)
            assert abs(result["overall_confidence"] - expected_avg) < 0.01

    @pytest.mark.asyncio
    async def test_pipeline_survives_recommendation_agent_failure(self):
        """If RecommendationAgent fails, pipeline must continue and produce a result."""
        from app.agents.orchestrator import AgentOrchestrator
        mock_llm = MagicMock()
        mock_llm.provider_name = "groq"

        call_count = 0

        async def llm_side_effect(prompt, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # QueryAnalysisAgent call
                return MagicMock(content='{"intent": "defect_diagnosis", "confidence": 0.85}')
            elif call_count >= 2:
                # RecommendationAgent + ReportAgent calls — recommendation raises first
                if call_count == 2:
                    raise Exception("Recommendation LLM timeout")
                return MagicMock(content="Executive Summary: Building in Fair condition.")

        mock_llm.generate = AsyncMock(side_effect=llm_side_effect)

        mock_pipeline = MagicMock()
        mock_pipeline.query = AsyncMock(return_value=_make_chat_response())

        orchestrator = AgentOrchestrator(llm_provider=mock_llm, rag_pipeline=mock_pipeline)

        with patch("app.agents.kg_reasoning_agent.get_defect_subgraph", new_callable=AsyncMock) as md, \
             patch("app.agents.kg_reasoning_agent.get_component_subgraph", new_callable=AsyncMock) as mc, \
             patch("app.agents.kg_reasoning_agent.get_repair_recommendations_from_kg", new_callable=AsyncMock) as mr:
            md.return_value = {}
            mc.return_value = {}
            mr.return_value = []

            # Must NOT raise
            result = await orchestrator.run(
                question="What causes spalling in columns?",
                top_k=5,
            )

        # Pipeline must complete and return a result
        assert "session_id" in result
        assert result["total_pipeline_ms"] > 0


# ===========================================================================
# 8. Schema Validation Tests
# ===========================================================================

class TestAgentSchemas:

    def test_agent_execution_step_schema_validates_confidence_range(self):
        """AgentExecutionStepSchema must reject confidence values outside [0, 1]."""
        from app.schemas.agents import AgentExecutionStepSchema
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            AgentExecutionStepSchema(
                agent="Test",
                status="success",
                time_ms=10.0,
                confidence=1.5,  # Invalid
                reason="Test reason",
            )

    def test_agent_pipeline_response_schema_complete(self):
        """AgentPipelineResponse must accept all required fields and serialize cleanly."""
        from app.schemas.agents import AgentPipelineResponse, AgentExecutionStepSchema

        response = AgentPipelineResponse(
            session_id="abc-123",
            question="What causes spalling?",
            rag_response=_make_chat_response(),
            report="## Executive Summary\n\nBuilding is in Fair condition.",
            execution_trace=[
                AgentExecutionStepSchema(
                    agent="QueryAnalysisAgent",
                    status="success",
                    time_ms=45.2,
                    confidence=0.93,
                    reason="Intent: defect_diagnosis. Defects: spalling.",
                )
            ],
            total_agents_run=1,
            total_pipeline_ms=500.0,
            pipeline_version="6.0",
            overall_confidence=0.93,
            domain_valid=True,
            query_intent="defect_diagnosis",
            enriched_kg_available=False,
        )

        assert response.pipeline_version == "6.0"
        assert response.execution_trace[0].reason == "Intent: defect_diagnosis. Defects: spalling."
        assert response.overall_confidence == 0.93

    def test_agent_pipeline_request_schema_validates_question_length(self):
        """AgentPipelineRequest must reject questions shorter than 3 chars."""
        from app.schemas.agents import AgentPipelineRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            AgentPipelineRequest(question="Hi", top_k=5)
