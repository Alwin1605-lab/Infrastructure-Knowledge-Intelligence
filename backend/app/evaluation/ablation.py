"""Ablation Experiments Runner for Phase 7.

Runs queries across 5 system configurations to measure the contribution
of each architectural component without code duplication:
    1. LLM-only (No RAG, raw LLM prompt)
    2. RAG-only (ChromaDB semantic search only)
    3. RAG + KG (ChromaDB + Neo4j entity matching)
    4. Hybrid RAG (Phase 5 pipeline)
    5. Hybrid RAG + Agentic AI (Phase 6 full orchestrator)
"""

import time
from typing import Any

from app.core.logging import get_logger
from app.services.rag_service import RAGService
from app.services.agent_service import AgentService
from app.llm.base import BaseLLMProvider

logger = get_logger(__name__)


class AblationRunner:
    """Executes evaluation queries against different architectural configurations."""

    def __init__(
        self,
        llm_provider: BaseLLMProvider,
        rag_service: RAGService,
        agent_service: AgentService,
    ) -> None:
        self.llm = llm_provider
        self.rag = rag_service
        self.agent = agent_service

    async def run_ablation(self, question: str, top_k: int = 5) -> dict[str, Any]:
        """Run a single question across all 5 configurations and collect metrics.

        Args:
            question: The test question.
            top_k: Document chunks to retrieve.

        Returns:
            Dictionary containing response and latency for each configuration.
        """
        results = {}

        # 1. LLM-only
        t0 = time.perf_counter_ns()
        try:
            llm_resp = await self.llm.generate(prompt=question, max_tokens=1000)
            llm_latency = (time.perf_counter_ns() - t0) / 1_000_000
            results["llm_only"] = {
                "answer": llm_resp.content,
                "latency_ms": round(llm_latency, 1),
            }
        except Exception as e:
            results["llm_only"] = {"error": str(e)}

        # 2. RAG-only (No KG, No Agent)
        # We simulate this by calling rag_service.run with include_kg=False
        try:
            rag_only_resp = await self.rag.run(question=question, top_k=top_k, include_kg=False)
            results["rag_only"] = {
                "answer": rag_only_resp.answer,
                "latency_ms": rag_only_resp.response_time.total_ms,
                "sources": len(rag_only_resp.sources),
                "confidence": rag_only_resp.confidence.score,
            }
        except Exception as e:
            results["rag_only"] = {"error": str(e)}

        # 3. RAG + KG (Phase 5 Full)
        try:
            rag_kg_resp = await self.rag.run(question=question, top_k=top_k, include_kg=True)
            results["rag_kg"] = {
                "answer": rag_kg_resp.answer,
                "latency_ms": rag_kg_resp.response_time.total_ms,
                "sources": len(rag_kg_resp.sources),
                "kg_entities": len(rag_kg_resp.kg_context),
                "confidence": rag_kg_resp.confidence.score,
            }
        except Exception as e:
            results["rag_kg"] = {"error": str(e)}

        # 4. Hybrid RAG + Agentic AI (Phase 6 Full)
        try:
            agent_resp = await self.agent.run(question=question, top_k=top_k, include_kg=True)
            results["agentic_ai"] = {
                "answer": agent_resp.get("rag_response").answer if agent_resp.get("rag_response") else agent_resp.get("report"),
                "report": agent_resp.get("report"),
                "latency_ms": agent_resp.get("total_pipeline_ms", 0),
                "confidence": agent_resp.get("overall_confidence", 0.0),
                "agents_run": agent_resp.get("total_agents_run", 0),
            }
        except Exception as e:
            results["agentic_ai"] = {"error": str(e)}

        return {
            "question": question,
            "ablation_results": results,
            "timestamp": time.time()
        }
