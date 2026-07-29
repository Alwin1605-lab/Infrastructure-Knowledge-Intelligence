"""FastAPI Evaluation Endpoints — Phase 7.

Exposes benchmarking, evaluation, and ablation testing for the pipeline.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.logging import get_logger
from app.schemas.evaluation import (
    BenchmarkRequest,
    BenchmarkResponse,
    AblationRequest,
    AblationResponse,
    EvaluationHistoryItem
)
from app.services.evaluation_service import EvaluationService

logger = get_logger(__name__)

router = APIRouter()


def get_evaluation_service(request: Request) -> EvaluationService:
    """Retrieve the EvaluationService singleton from application state."""
    service = getattr(request.app.state, "evaluation_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Evaluation pipeline is not initialized.",
        )
    return service


EvaluationServiceDep = Annotated[EvaluationService, Depends(get_evaluation_service)]


@router.post(
    "/benchmark",
    response_model=BenchmarkResponse,
    summary="Run Benchmark Suite",
    description="Run the evaluation dataset against the agentic pipeline and generate reports.",
)
async def run_benchmark(
    request: BenchmarkRequest,
    eval_service: EvaluationServiceDep,
) -> BenchmarkResponse:
    """Execute the benchmark suite."""
    logger.info("benchmark_started", category=request.category, top_k=request.top_k)
    try:
        result = await eval_service.run_benchmark(
            category=request.category,
            top_k=request.top_k,
        )
        return BenchmarkResponse(**result)
    except Exception as exc:
        logger.error("benchmark_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Benchmark execution error: {exc}",
        ) from exc


@router.get(
    "/history",
    response_model=list[EvaluationHistoryItem],
    summary="List Benchmark History",
    description="Retrieve past benchmark runs saved in the evaluation_results directory.",
)
async def list_history(eval_service: EvaluationServiceDep) -> list[EvaluationHistoryItem]:
    """List historical benchmark runs."""
    try:
        history = eval_service.list_history()
        return [EvaluationHistoryItem(**item) for item in history]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load history: {exc}",
        ) from exc


@router.post(
    "/ablation",
    response_model=AblationResponse,
    summary="Run Ablation Experiment",
    description="Test a query across 5 system configurations to measure architectural improvements.",
)
async def run_ablation(
    request: AblationRequest,
    eval_service: EvaluationServiceDep,
) -> AblationResponse:
    """Execute ablation test."""
    logger.info("ablation_started", question=request.question[:80])
    try:
        result = await eval_service.run_ablation(
            question=request.question,
            top_k=request.top_k,
        )
        return AblationResponse(**result)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ablation execution error: {exc}",
        ) from exc
