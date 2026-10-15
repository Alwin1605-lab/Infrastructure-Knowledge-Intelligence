from app.models.document import Document
from typing import Dict, Any

class KnowledgeGapService:
    @staticmethod
    async def get_gaps() -> Dict[str, Any]:
        """Query Document to find counts per category and identify gaps."""
        # Note: Depending on the specific implementation of Document, we might aggregate by metadata tags or categories.
        # Here we do a basic aggregation assuming a category field exists, or mock if needed.
        # Beanie provides aggregation capabilities. We'll do a mock or basic one.
        
        pipeline = [
            {"$group": {"_id": "$metadata.category", "count": {"$sum": 1}}}
        ]
        
        results = await Document.aggregate(pipeline).to_list()
        
        gaps = []
        category_counts = {}
        for res in results:
            cat = res.get("_id")
            if cat is None:
                cat = "Uncategorized"
            count = res.get("count", 0)
            category_counts[cat] = count
            if count < 5:
                gaps.append({"category": cat, "count": count, "message": "Low document count"})
                
        return {
            "category_counts": category_counts,
            "identified_gaps": gaps
        }
