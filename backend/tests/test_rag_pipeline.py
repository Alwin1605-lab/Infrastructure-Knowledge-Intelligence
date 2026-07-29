"""Unit and integration tests for Phase 5 — Hybrid RAG Pipeline.

Tests cover:
    1. QueryProcessor — domain rejection, entity extraction, query expansion
    2. ChunkReranker — entity-boosted scoring and filtering
    3. ContextFuser — prompt assembly and truncation
    4. ConfidenceScorer — grounding classification and numeric scoring
    5. ResponseParser — ChatResponse assembly from mock data
    6. HybridRAGPipeline — end-to-end with mock retriever and KG (no live DB)
"""

import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.rag.query_processor import QueryProcessor
from app.rag.reranker import ChunkReranker
from app.rag.context_fusion import ContextFuser
from app.rag.confidence import ConfidenceScorer
from app.rag.response_parser import ResponseParser
from app.vectorstore.retriever import RetrievedChunk
from app.schemas.chat import ChatRequest, ConfidenceScore


# ---------------------------------------------------------------------------
# Helper: build a mock RetrievedChunk
# ---------------------------------------------------------------------------

def make_chunk(
    text: str,
    doc_name: str = "CPWD_Maintenance_Manual.pdf",
    relevance: float = 0.80,
    page: int = 42,
    section: str = "4.3 Spalling",
) -> RetrievedChunk:
    return RetrievedChunk(
        text=text,
        document_id="doc_cpwd_001",
        document_name=doc_name,
        relevance_score=relevance,
        page_number=page,
        section=section,
    )


# ===========================================================================
# 1. QueryProcessor Tests
# ===========================================================================

class TestQueryProcessor:

    def setup_method(self):
        self.processor = QueryProcessor()

    def test_domain_rejection_highway_bridge(self):
        """Non-building query (highway bridge) must be rejected."""
        result = self.processor.preprocess("How to inspect a highway bridge for corrosion?")
        assert result.is_building_domain is False
        assert result.rejection_reason is not None
        assert "highway bridge" in result.rejection_reason.lower() or "non-building" in result.rejection_reason.lower()

    def test_domain_rejection_railway_bridge(self):
        """Railway bridge query must be rejected."""
        result = self.processor.preprocess("What is the IRC code for railway bridge maintenance?")
        assert result.is_building_domain is False

    def test_building_query_accepted(self):
        """Valid building query must pass domain guard."""
        result = self.processor.preprocess("What causes spalling in RCC columns?")
        assert result.is_building_domain is True
        assert result.rejection_reason is None

    def test_defect_extraction(self):
        """Spalling and corrosion must be extracted from the query."""
        result = self.processor.preprocess("Explain spalling and corrosion in concrete beams.")
        assert "spalling" in result.extracted_defects
        assert "corrosion" in result.extracted_defects

    def test_component_extraction(self):
        """Column and slab must be extracted as building components."""
        result = self.processor.preprocess("Inspect column and slab for honeycombing defects.")
        assert "column" in result.extracted_components
        assert "slab" in result.extracted_components

    def test_query_expansion_adds_synonyms(self):
        """Expanded query must contain synonyms not in the original."""
        result = self.processor.preprocess("What are causes of crack in a beam?")
        assert len(result.expanded_query) > len(result.original_query)

    def test_kg_search_terms_populated(self):
        """KG search terms must include the defect and component found."""
        result = self.processor.preprocess("How does seepage affect the foundation?")
        assert len(result.kg_search_terms) > 0

    def test_empty_query_accepted_gracefully(self):
        """Empty/whitespace query must not raise; returns minimal ProcessedQuery."""
        result = self.processor.preprocess("   ")
        # Domain guard passes (no exclusion match), entity lists may be empty
        assert result.is_building_domain is True
        assert result.extracted_defects == []


# ===========================================================================
# 2. ChunkReranker Tests
# ===========================================================================

class TestChunkReranker:

    def setup_method(self):
        self.reranker = ChunkReranker(min_final_score=0.20)

    def test_empty_input_returns_empty(self):
        from app.rag.query_processor import ProcessedQuery
        pq = ProcessedQuery(original_query="test", expanded_query="test")
        result = self.reranker.rerank([], pq)
        assert result == []

    def test_entity_match_boosts_score(self):
        """Chunk containing the query defect entity must score higher than one that doesn't."""
        from app.rag.query_processor import ProcessedQuery
        pq = ProcessedQuery(
            original_query="spalling in column",
            expanded_query="spalling in column",
            extracted_defects=["spalling"],
            extracted_components=["column"],
        )
        chunk_relevant = make_chunk(
            "Spalling occurs in column surfaces due to corrosion of reinforcement.",
            relevance=0.55,
        )
        chunk_irrelevant = make_chunk(
            "The document was published in 2019 by CPWD.",
            relevance=0.55,
        )
        result = self.reranker.rerank([chunk_relevant, chunk_irrelevant], pq)
        assert len(result) >= 1
        # The chunk with entity match should have higher final_score
        assert result[0].chunk.text == chunk_relevant.text

    def test_low_score_chunks_filtered(self):
        """Chunk with very low relevance must be filtered out."""
        from app.rag.query_processor import ProcessedQuery
        pq = ProcessedQuery(original_query="test", expanded_query="test")
        low_chunk = make_chunk("Irrelevant text.", relevance=0.05)
        result = self.reranker.rerank([low_chunk], pq)
        assert result == []

    def test_final_score_does_not_exceed_one(self):
        """Final score must always be ≤ 1.0 regardless of entity boost."""
        from app.rag.query_processor import ProcessedQuery
        pq = ProcessedQuery(
            original_query="spalling corrosion crack column beam slab",
            expanded_query="spalling corrosion crack column beam slab",
            extracted_defects=["spalling", "corrosion", "crack"],
            extracted_components=["column", "beam", "slab"],
        )
        chunk = make_chunk(
            "Spalling corrosion crack in column beam slab detected.",
            relevance=0.95,
        )
        result = self.reranker.rerank([chunk], pq)
        assert result[0].final_score <= 1.0


# ===========================================================================
# 3. ConfidenceScorer Tests
# ===========================================================================

class TestConfidenceScorer:

    def setup_method(self):
        self.scorer = ConfidenceScorer()

    def _make_ranked_chunks(self, count: int, top_score: float = 0.85):
        from app.rag.reranker import RankedChunk
        return [
            RankedChunk(
                chunk=make_chunk("Chunk text", relevance=top_score),
                semantic_score=top_score,
                entity_boost=0.0,
                final_score=top_score,
                matched_entities=[],
            )
            for _ in range(count)
        ]

    def test_rag_and_kg_grounding(self):
        """With both chunks and KG entities, grounding must be rag_and_kg."""
        ranked = self._make_ranked_chunks(3)
        score = self.scorer.score(ranked, num_kg_entities=4, question="test")
        assert score.grounding == "rag_and_kg"
        assert score.level in ("high", "medium")

    def test_rag_only_grounding(self):
        """With chunks but no KG entities, grounding must be rag_only."""
        ranked = self._make_ranked_chunks(2, top_score=0.70)
        score = self.scorer.score(ranked, num_kg_entities=0, question="test")
        assert score.grounding == "rag_only"

    def test_kg_only_grounding(self):
        """With no chunks but KG entities, grounding must be kg_only."""
        score = self.scorer.score([], num_kg_entities=3, question="test")
        assert score.grounding == "kg_only"

    def test_insufficient_grounding(self):
        """With no chunks and no KG entities, grounding must be insufficient_context."""
        score = self.scorer.score([], num_kg_entities=0, question="test")
        assert score.grounding == "insufficient_context"
        assert score.level == "insufficient"
        assert score.score < 0.25

    def test_high_confidence_requires_good_retrieval(self):
        """High confidence requires a top chunk score ≥ 0.75 with KG support."""
        ranked = self._make_ranked_chunks(5, top_score=0.88)
        score = self.scorer.score(ranked, num_kg_entities=5, question="test")
        assert score.level == "high"
        assert score.score >= 0.75


# ===========================================================================
# 4. ResponseParser Tests
# ===========================================================================

class TestResponseParser:

    def _make_parser(self):
        start_ns = time.perf_counter_ns() - 1_000_000_000
        return ResponseParser(
            start_time_ns=start_ns,
            retrieval_ms=180.0,
            kg_lookup_ms=55.0,
            llm_start_ns=time.perf_counter_ns() - 500_000_000,
        )

    def _make_ranked_chunks(self):
        from app.rag.reranker import RankedChunk
        return [
            RankedChunk(
                chunk=make_chunk("Spalling in RCC column is caused by corrosion of reinforcement bars."),
                semantic_score=0.85,
                entity_boost=0.08,
                final_score=0.93,
                matched_entities=["spalling", "column"],
            )
        ]

    def test_sources_built_from_chunks(self):
        parser = self._make_parser()
        ranked = self._make_ranked_chunks()
        confidence = ConfidenceScore(score=0.85, level="high", grounding="rag_and_kg",
                                     reasoning="Good retrieval.")
        response = parser.parse(
            llm_text="## Answer\n\nSpalling is caused by corrosion of rebar.\n## Recommendations\n- Conduct half-cell potential test.",
            ranked_chunks=ranked,
            kg_data={},
            confidence=confidence,
            question="What causes spalling in RCC columns?",
        )
        assert len(response.sources) == 1
        assert response.sources[0].document_name == "CPWD_Maintenance_Manual.pdf"
        assert response.sources[0].page == 42
        assert response.sources[0].relevance_score == 0.93

    def test_response_has_all_7_fields(self):
        parser = self._make_parser()
        ranked = self._make_ranked_chunks()
        confidence = ConfidenceScore(score=0.80, level="high", grounding="rag_only",
                                     reasoning="2 chunks retrieved.")
        response = parser.parse(
            llm_text="Spalling is caused by rebar corrosion.",
            ranked_chunks=ranked,
            kg_data={},
            confidence=confidence,
            question="Spalling causes?",
        )
        assert response.answer
        assert isinstance(response.sources, list)
        assert isinstance(response.kg_context, list)
        assert response.confidence is not None
        assert isinstance(response.recommendations, list)
        assert isinstance(response.related_components, list)
        assert response.response_time.total_ms > 0

    def test_kg_context_built_from_defect_subgraph(self):
        parser = self._make_parser()
        ranked = self._make_ranked_chunks()
        confidence = ConfidenceScore(score=0.78, level="high", grounding="rag_and_kg",
                                     reasoning="Good.")
        kg_data = {
            "defects_found": [{
                "defect": "spalling",
                "causes": ["corrosion", "carbonation"],
                "repairs": [{"repair": "concrete jacketing", "standard": "IS 456"}],
                "affected_components": ["column", "beam"],
            }]
        }
        response = parser.parse(
            llm_text="Spalling causes and repairs.",
            ranked_chunks=ranked,
            kg_data=kg_data,
            confidence=confidence,
            question="Spalling?",
        )
        assert len(response.kg_context) >= 1
        entity = response.kg_context[0]
        assert entity.entity == "spalling"
        assert entity.type == "Defect"
        assert any(r.type == "CAUSED_BY" for r in entity.relationships)
        assert any(r.type == "REPAIRED_BY" for r in entity.relationships)


# ===========================================================================
# 5. End-to-End Pipeline Integration Test (Mock DB)
# ===========================================================================

class TestHybridRAGPipelineIntegration:

    @pytest.mark.asyncio
    async def test_pipeline_returns_chat_response_with_mock_retriever(self):
        """Full pipeline run with mocked ChromaDB and KG — no live DB required."""
        from app.rag.pipeline import HybridRAGPipeline
        from app.rag.reranker import RankedChunk

        # Mock LLM provider
        mock_llm = MagicMock()
        mock_llm.provider_name = "groq"
        mock_llm.generate = AsyncMock(return_value=MagicMock(
            content="## Answer\n\nSpalling in RCC columns is primarily caused by corrosion "
                    "of embedded steel reinforcement bars. The corrosion products expand, "
                    "generating pressure that cracks the concrete cover.\n\n"
                    "## Recommendations\n\n- Conduct half-cell potential test urgently\n"
                    "- Apply epoxy injection to cracks\n\n"
                    "**Confidence**: High"
        ))

        # Mock embedding service
        mock_embedding = MagicMock()

        # Mock ChromaRetriever
        mock_retriever = MagicMock()
        mock_retriever.retrieve = AsyncMock(return_value=[
            make_chunk(
                "Spalling in RCC columns occurs when reinforcement corrodes. "
                "The steel oxidises and expands, causing the concrete cover to crack and spall.",
                relevance=0.88,
            )
        ])

        # Patch KG query functions to avoid live Neo4j
        with patch("app.rag.pipeline.get_defect_subgraph", new_callable=AsyncMock) as mock_defect, \
             patch("app.rag.pipeline.get_component_subgraph", new_callable=AsyncMock) as mock_comp, \
             patch("app.rag.pipeline.search_entities_by_text", new_callable=AsyncMock) as mock_search:

            mock_defect.return_value = {
                "defects_found": [{
                    "defect": "spalling",
                    "causes": ["corrosion"],
                    "repairs": [{"repair": "concrete jacketing", "standard": "IS 456"}],
                    "affected_components": ["column"],
                }]
            }
            mock_comp.return_value = {}
            mock_search.return_value = []

            pipeline = HybridRAGPipeline(
                llm_provider=mock_llm,
                embedding_service=mock_embedding,
                retriever=mock_retriever,
            )

            request = ChatRequest(
                question="What causes spalling in RCC columns and how should it be repaired?",
                include_kg_context=True,
                top_k=5,
            )

            response = await pipeline.query(request)

        # Validate all 7 fields are populated
        assert len(response.answer) > 30
        assert len(response.sources) == 1
        assert response.sources[0].document_name == "CPWD_Maintenance_Manual.pdf"
        assert len(response.kg_context) >= 1
        assert response.confidence.grounding in ("rag_and_kg", "rag_only")
        assert response.confidence.score > 0.0
        assert isinstance(response.recommendations, list)
        assert response.response_time.total_ms > 0

    @pytest.mark.asyncio
    async def test_pipeline_rejects_non_building_query(self):
        """Pipeline must return rejection response for highway bridge query."""
        from app.rag.pipeline import HybridRAGPipeline

        mock_llm = MagicMock()
        mock_embedding = MagicMock()
        mock_retriever = MagicMock()
        mock_retriever.retrieve = AsyncMock(return_value=[])

        pipeline = HybridRAGPipeline(
            llm_provider=mock_llm,
            embedding_service=mock_embedding,
            retriever=mock_retriever,
        )

        request = ChatRequest(
            question="How do you inspect a highway bridge for structural defects?",
            include_kg_context=True,
            top_k=5,
        )

        response = await pipeline.query(request)

        assert response.confidence.grounding == "insufficient_context"
        assert response.confidence.level == "insufficient"
        assert "building" in response.answer.lower() or "restricted" in response.answer.lower()
        # LLM should never have been called
        mock_llm.generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_pipeline_survives_kg_failure(self):
        """If KG traversal raises, pipeline must continue with rag_only grounding."""
        from app.rag.pipeline import HybridRAGPipeline

        mock_llm = MagicMock()
        mock_llm.provider_name = "groq"
        mock_llm.generate = AsyncMock(return_value=MagicMock(
            content="Spalling is caused by rebar corrosion. **Confidence**: Medium"
        ))
        mock_embedding = MagicMock()
        mock_retriever = MagicMock()
        mock_retriever.retrieve = AsyncMock(return_value=[
            make_chunk("Spalling occurs when rebar corrodes.", relevance=0.72)
        ])

        with patch("app.rag.pipeline.get_defect_subgraph", new_callable=AsyncMock) as mock_defect:
            mock_defect.side_effect = Exception("Neo4j connection refused")

            pipeline = HybridRAGPipeline(
                llm_provider=mock_llm,
                embedding_service=mock_embedding,
                retriever=mock_retriever,
            )

            request = ChatRequest(
                question="What causes spalling in columns?",
                include_kg_context=True,
                top_k=5,
            )

            # Must NOT raise — should gracefully handle KG failure
            response = await pipeline.query(request)

        assert response.answer
        assert response.confidence.grounding in ("rag_only", "insufficient_context")
        assert response.response_time.total_ms > 0
