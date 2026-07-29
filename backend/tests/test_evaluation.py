"""Tests for Phase 7: Evaluation, Benchmarking, and Explainability Framework."""

import os
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.evaluation.dataset import BenchmarkDatasetManager, BenchmarkQuestion
from app.evaluation.metrics import (
    RetrievalCoverageEvaluator,
    MRREvaluator,
    HitRateEvaluator,
    CitationCorrectnessEvaluator,
    ResponseCompletenessEvaluator,
    RecommendationQualityEvaluator,
)
from app.evaluation.error_analysis import ErrorAnalyzer
from app.evaluation.explainability import ExplainabilityGenerator
from app.evaluation.persistence import BenchmarkPersistence
from app.services.evaluation_service import EvaluationService
from app.schemas.chat import (
    ChatResponse, ConfidenceScore, SourceDocument, EngineeringRecommendation, ResponseTime
)

# ---------------------------------------------------------------------------
# 1. Dataset Tests
# ---------------------------------------------------------------------------
def test_dataset_manager_loads_builtin():
    manager = BenchmarkDatasetManager()
    questions = manager.load_dataset()
    assert len(questions) > 0
    categories = manager.get_categories()
    assert "defects" in categories
    
    defect_questions = manager.load_dataset("defects")
    assert all(q.category == "defects" for q in defect_questions)


def test_dataset_load_from_json(tmp_path):
    manager = BenchmarkDatasetManager()
    initial_count = len(manager.load_dataset())
    
    json_path = tmp_path / "test_data.json"
    with open(json_path, "w") as f:
        json.dump({
            "questions": [
                {"id": "t1", "category": "test", "question": "Q1?"}
            ]
        }, f)
        
    manager.load_from_json(json_path)
    assert len(manager.load_dataset()) == initial_count + 1
    assert "test" in manager.get_categories()


# ---------------------------------------------------------------------------
# 2. Metrics Tests
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_retrieval_coverage():
    evaluator = RetrievalCoverageEvaluator()
    res = await evaluator.evaluate(
        expected_keywords=["spalling", "corrosion", "rebar"],
        retrieved_texts=["Spalling is often caused by rebar corrosion."]
    )
    assert res.score == 1.0
    
    res2 = await evaluator.evaluate(
        expected_keywords=["spalling", "corrosion", "rebar"],
        retrieved_texts=["Spalling occurs in concrete."]
    )
    assert round(res2.score, 2) == 0.33


@pytest.mark.asyncio
async def test_mrr_evaluator():
    evaluator = MRREvaluator()
    res = await evaluator.evaluate(
        expected_chunk_ids=["chunk3", "chunk5"],
        retrieved_chunk_ids=["chunk1", "chunk2", "chunk3"]
    )
    assert round(res.score, 2) == 0.33  # Rank 3 -> 1/3


@pytest.mark.asyncio
async def test_hit_rate_evaluator():
    evaluator = HitRateEvaluator()
    res = await evaluator.evaluate(
        expected_chunk_ids=["chunk3"],
        retrieved_chunk_ids=["chunk1", "chunk2", "chunk3"]
    )
    assert res.score == 1.0


@pytest.mark.asyncio
async def test_citation_correctness():
    evaluator = CitationCorrectnessEvaluator()
    res = await evaluator.evaluate(
        expected_keywords=["corrosion", "carbonation"],
        cited_texts=["Corrosion of steel is the main cause."]
    )
    assert res.score == 0.5


@pytest.mark.asyncio
async def test_response_completeness():
    evaluator = ResponseCompletenessEvaluator()
    res = await evaluator.evaluate(
        expected_keywords=["jacketing", "epoxy"],
        answer="The repair involves concrete jacketing and epoxy injection."
    )
    assert res.score == 1.0


@pytest.mark.asyncio
async def test_recommendation_quality():
    evaluator = RecommendationQualityEvaluator()
    class Rec:
        def __init__(self, p):
            self.priority = p
            
    res = await evaluator.evaluate(
        recommendations=[Rec("high"), Rec("low")]
    )
    # score = min(1.0, 0.5 + (0.1 * 2) + (0.2 * 1)) = 0.5 + 0.2 + 0.2 = 0.9
    assert round(res.score, 2) == 0.9


# ---------------------------------------------------------------------------
# 3. Error Analysis Tests
# ---------------------------------------------------------------------------
def test_error_analysis_poor_retrieval():
    eval_results = {"hit_rate": {"score": 0.0}, "response_completeness": {"score": 0.0}}
    rag_resp = ChatResponse(
        answer="I don't know", 
        sources=[], 
        kg_context=[], 
        confidence=ConfidenceScore(score=0.9, level="high", grounding="rag_only", reasoning=""),
        response_time=ResponseTime(total_ms=10.0, retrieval_ms=5.0, kg_lookup_ms=0.0, llm_generation_ms=5.0, post_processing_ms=0.0)
    )
    reason = ErrorAnalyzer.classify_failure("defects", ["spalling"], rag_resp, eval_results)
    assert reason == "Missing Documents"

def test_error_analysis_is_failure():
    assert ErrorAnalyzer.is_failure({"hit_rate": {"score": 0.0}}) is True
    assert ErrorAnalyzer.is_failure({"hit_rate": {"score": 1.0}, "response_completeness": {"score": 1.0}}) is False


# ---------------------------------------------------------------------------
# 4. Explainability & Persistence Tests
# ---------------------------------------------------------------------------
def test_markdown_generation():
    payload = {
        "summary": {"questions_tested": 10, "accuracy_percent": 80.0},
        "failure_breakdown": {"Poor Retrieval": 2},
        "config_comparison": {"best_configuration": "Hybrid RAG + Agentic AI", "retrieval_improvement_percent": 15.0}
    }
    md = ExplainabilityGenerator.generate_markdown_report(payload)
    assert "Benchmark Evaluation Report" in md
    assert "**Questions Tested:** 10" in md
    assert "Poor Retrieval:** 2" in md
    assert "15.0%** Retrieval Accuracy" in md


def test_persistence_save_and_list(tmp_path):
    persistence = BenchmarkPersistence(base_dir=tmp_path)
    res = persistence.save_benchmark({"summary": {"questions_tested": 5}}, "# Report")
    
    assert os.path.exists(res["json_file"])
    assert os.path.exists(res["md_file"])
    
    history = persistence.list_history()
    assert len(history) == 1
    assert history[0]["questions_tested"] == 5


# ---------------------------------------------------------------------------
# 5. EvaluationService Integration Test
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_evaluation_service_run_benchmark(tmp_path):
    mock_llm = AsyncMock()
    mock_rag = AsyncMock()
    mock_agent = AsyncMock()
    
    mock_agent.run.return_value = {
        "rag_response": ChatResponse(
            answer="Test answer", 
            sources=[SourceDocument(document_name="doc1", page=1, chunk_preview="test", relevance_score=0.9)],
            kg_context=[],
            confidence=ConfidenceScore(score=0.9, level="high", grounding="rag_only", reasoning=""),
            response_time=ResponseTime(total_ms=10.0, retrieval_ms=5.0, kg_lookup_ms=0.0, llm_generation_ms=5.0, post_processing_ms=0.0)
        ),
        "total_pipeline_ms": 100,
        "overall_confidence": 0.9,
        "execution_trace": []
    }
    
    mock_ablation = AsyncMock()
    mock_ablation.run_ablation.return_value = {}
    
    eval_service = EvaluationService(mock_llm, mock_rag, mock_agent)
    eval_service.persistence = BenchmarkPersistence(base_dir=tmp_path)
    eval_service.ablation_runner = mock_ablation
    
    # Run only 1 item to make it fast
    with patch.object(eval_service.dataset_manager, 'load_dataset', return_value=[BenchmarkQuestion("1", "test", "Q", ["test"], ["doc1"])]):
        result = await eval_service.run_benchmark()
        
    assert result["summary"]["questions_tested"] == 1
    assert os.path.exists(result["json_report_path"])
