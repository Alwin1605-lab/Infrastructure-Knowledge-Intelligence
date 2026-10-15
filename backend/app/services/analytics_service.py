"""Analytics Service — aggregates platform statistics for dashboards.

Provides:
    - Knowledge base statistics (docs, chunks, KG nodes)
    - Query performance metrics
    - Citation frequency analysis
    - Document category distribution
    - KB growth over time (by week)
"""

from datetime import datetime, timezone, timedelta
from typing import Any
from collections import defaultdict

from app.models.document import Document, DocumentStatus
from app.models.query_metric import QueryMetric
from app.models.processing_job import ProcessingJob, JobStatus
from app.core.logging import get_logger

logger = get_logger(__name__)


class AnalyticsService:
    """Aggregates statistics across the platform for analytics dashboards."""
    
    async def get_kb_stats(self) -> dict[str, Any]:
        """Get overall knowledge base statistics."""
        try:
            total_docs = await Document.find({"status": DocumentStatus.COMPLETED}).count()
            total_chunks = await self._sum_field(Document, "total_chunks")
            total_kg_entities = await self._sum_field(Document, "total_kg_entities")
            total_kg_relationships = await self._sum_field(Document, "total_kg_relationships")
            total_pages = await self._sum_field(Document, "total_pages")
            failed_docs = await Document.find({"status": DocumentStatus.FAILED}).count()
            processing_docs = await Document.find({"status": {"$nin": [DocumentStatus.COMPLETED, DocumentStatus.FAILED]}}).count()
            
            # Category distribution
            all_docs = await Document.find_all().to_list()
            category_dist = defaultdict(int)
            for doc in all_docs:
                cat = getattr(doc, 'category', 'GENERAL')
                category_dist[str(cat)] += 1
            
            return {
                "total_documents": total_docs,
                "total_chunks": total_chunks,
                "total_embeddings": total_chunks,  # 1 embedding per chunk
                "total_kg_entities": total_kg_entities,
                "total_kg_relationships": total_kg_relationships,
                "total_pages": total_pages,
                "failed_documents": failed_docs,
                "processing_documents": processing_docs,
                "category_distribution": dict(category_dist),
            }
        except Exception as exc:
            logger.error("kb_stats_failed", error=str(exc))
            return {}
    
    async def get_kb_growth(self, days: int = 30) -> list[dict]:
        """Get document count growth over the last N days."""
        try:
            since = datetime.now(timezone.utc) - timedelta(days=days)
            docs = await Document.find({"created_at": {"$gte": since}}).to_list()
            
            # Group by date
            by_date = defaultdict(lambda: {"documents": 0, "chunks": 0})
            for doc in docs:
                date_key = doc.created_at.strftime("%Y-%m-%d")
                by_date[date_key]["documents"] += 1
                by_date[date_key]["chunks"] += doc.total_chunks
            
            # Fill in missing days
            result = []
            for i in range(days):
                date = (datetime.now(timezone.utc) - timedelta(days=days-i-1)).strftime("%Y-%m-%d")
                entry = by_date.get(date, {"documents": 0, "chunks": 0})
                result.append({"date": date, **entry})
            
            return result
        except Exception as exc:
            logger.error("kb_growth_failed", error=str(exc))
            return []
    
    async def get_query_metrics_summary(self) -> dict[str, Any]:
        """Summarize query performance metrics."""
        try:
            total_queries = await QueryMetric.count()
            if total_queries == 0:
                return {"total_queries": 0}
            
            all_metrics = await QueryMetric.find_all().to_list()
            
            avg_total = sum(m.total_time_ms for m in all_metrics) / len(all_metrics)
            avg_retrieval = sum(m.retrieval_time_ms for m in all_metrics) / len(all_metrics)
            avg_llm = sum(m.llm_time_ms for m in all_metrics) / len(all_metrics)
            avg_embedding = sum(m.embedding_time_ms for m in all_metrics) / len(all_metrics)
            avg_chunks = sum(m.chunks_retrieved for m in all_metrics) / len(all_metrics)
            
            # Slowest queries (top 5)
            sorted_by_time = sorted(all_metrics, key=lambda m: m.total_time_ms, reverse=True)
            slowest = [
                {"question": m.question[:80], "total_ms": round(m.total_time_ms)}
                for m in sorted_by_time[:5]
            ]
            
            return {
                "total_queries": total_queries,
                "avg_total_ms": round(avg_total, 1),
                "avg_retrieval_ms": round(avg_retrieval, 1),
                "avg_llm_ms": round(avg_llm, 1),
                "avg_embedding_ms": round(avg_embedding, 1),
                "avg_chunks_retrieved": round(avg_chunks, 1),
                "slowest_queries": slowest,
            }
        except Exception as exc:
            logger.error("query_metrics_failed", error=str(exc))
            return {"total_queries": 0}
    
    async def get_processing_queue_stats(self) -> dict[str, Any]:
        """Get current processing queue status."""
        try:
            queued = await ProcessingJob.find({"status": JobStatus.QUEUED}).count()
            running = await ProcessingJob.find({"status": JobStatus.RUNNING}).count()
            completed = await ProcessingJob.find({"status": JobStatus.COMPLETED}).count()
            failed = await ProcessingJob.find({"status": JobStatus.FAILED}).count()
            return {
                "queued": queued,
                "running": running,
                "completed": completed,
                "failed": failed,
                "total": queued + running + completed + failed
            }
        except Exception as exc:
            logger.error("queue_stats_failed", error=str(exc))
            return {"queued": 0, "running": 0, "completed": 0, "failed": 0, "total": 0}
    
    async def _sum_field(self, model, field: str) -> int:
        """Sum an integer field across all documents."""
        try:
            docs = await model.find_all().to_list()
            return sum(getattr(doc, field, 0) or 0 for doc in docs)
        except Exception:
            return 0
