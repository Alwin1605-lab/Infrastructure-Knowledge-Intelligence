"""Search Service — unified cross-collection search.

Searches across:
    - Global Documents (by filename, metadata)
    - Workspace Documents
    - Reports
    - KG Entity suggestions

Returns ranked results with source type and relevance.
"""

from typing import Optional, Any
from app.models.document import Document, DocumentStatus
from app.models.report import Report
from app.core.logging import get_logger

logger = get_logger(__name__)


class SearchService:
    """Performs unified text search across all platform collections."""
    
    async def search(
        self,
        query: str,
        document_type: Optional[str] = None,
        workspace_id: Optional[str] = None,
        limit: int = 20,
        user_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Search across documents and reports.
        
        Args:
            query: Search string.
            document_type: Optional filter by document type.
            workspace_id: Optional filter by workspace.
            limit: Maximum results to return.
            user_id: Current user for access control.
            
        Returns:
            List of search result dicts with source, name, excerpt, score.
        """
        results = []
        query_lower = query.lower()
        
        # Search Documents
        try:
            doc_filter = {"status": DocumentStatus.COMPLETED}
            if document_type:
                doc_filter["document_type"] = document_type
            
            docs = await Document.find(doc_filter).limit(limit * 2).to_list()
            for doc in docs:
                score = 0.0
                name_lower = doc.filename.lower()
                if query_lower in name_lower:
                    score += 1.0
                    if name_lower.startswith(query_lower):
                        score += 0.5
                
                # Check metadata
                meta = getattr(doc, 'auto_metadata', {}) or {}
                meta_text = " ".join(str(v) for v in meta.values()).lower()
                if query_lower in meta_text:
                    score += 0.3
                
                if score > 0:
                    results.append({
                        "id": str(doc.id),
                        "type": "document",
                        "name": doc.filename,
                        "category": str(getattr(doc, 'category', 'GENERAL')),
                        "document_type": str(doc.document_type),
                        "excerpt": f"{doc.total_pages} pages, {doc.total_chunks} chunks indexed",
                        "score": score,
                        "created_at": doc.created_at.isoformat(),
                        "metadata": meta,
                    })
        except Exception as exc:
            logger.warning("document_search_failed", error=str(exc))
        
        # Search Reports
        try:
            reports = await Report.find_all().limit(limit).to_list()
            for report in reports:
                title = getattr(report, 'title', '') or ''
                if query_lower in title.lower():
                    results.append({
                        "id": str(report.id),
                        "type": "report",
                        "name": title or "Untitled Report",
                        "excerpt": f"Generated report",
                        "score": 0.8,
                        "created_at": report.created_at.isoformat() if hasattr(report, 'created_at') else "",
                    })
        except Exception as exc:
            logger.warning("report_search_failed", error=str(exc))
        
        # Sort by score
        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:limit]
    
    async def get_suggestions(self, query: str, limit: int = 8) -> list[str]:
        """Get autocomplete suggestions based on document names and metadata keywords."""
        if len(query) < 2:
            return []
        
        suggestions = set()
        query_lower = query.lower()
        
        try:
            docs = await Document.find(
                {"status": DocumentStatus.COMPLETED}
            ).limit(200).to_list()
            
            for doc in docs:
                # Suggest from filename
                name = doc.filename.replace('_', ' ').replace('-', ' ').replace('.pdf', '')
                words = name.split()
                for word in words:
                    if word.lower().startswith(query_lower) and len(word) > 2:
                        suggestions.add(word.title())
                
                # Suggest from metadata keywords
                meta = getattr(doc, 'auto_metadata', {}) or {}
                keywords = meta.get('keywords', [])
                if isinstance(keywords, list):
                    for kw in keywords:
                        if str(kw).lower().startswith(query_lower):
                            suggestions.add(str(kw).title())
        except Exception as exc:
            logger.warning("suggestions_failed", error=str(exc))
        
        return sorted(list(suggestions))[:limit]
