"""Document Relationships Detection Service.

Automatically detects documents discussing the same topics, citing similar standards,
and covering shared defects/repair methods. Generates structured relationships for
GraphRAG context enrichment and recommendation engines.
"""

from typing import Any
from app.core.logging import get_logger
from app.curation.models import CurationRecord, CurationStatus

logger = get_logger(__name__)


class DocumentRelationshipBuilder:
    """Detects inter-document relationships by analyzing shared topics, standards, and defects."""

    def build_relationships(self, records: list[CurationRecord]) -> list[dict[str, Any]]:
        """Compare all approved records pairwise and construct relationship graphs.

        Returns:
            list[dict] formatted for `knowledge_base/document_relationships.json`.
        """
        approved = [r for r in records if r.status == CurationStatus.APPROVED.value]
        results: list[dict[str, Any]] = []

        for rec_a in approved:
            doc_id_a = rec_a.metadata.document_id
            name_a = rec_a.metadata.file_name
            topics_a = set(t.lower() for t in rec_a.analysis.main_topics)
            standards_a = set(s.upper() for s in rec_a.analysis.standards_mentioned)
            defects_a = set(d.lower() for d in rec_a.analysis.defects_mentioned)
            repairs_a = set(r.lower() for r in rec_a.analysis.repair_methods)

            related_list: list[dict[str, Any]] = []

            for rec_b in approved:
                if rec_a.metadata.document_id == rec_b.metadata.document_id:
                    continue

                doc_id_b = rec_b.metadata.document_id
                name_b = rec_b.metadata.file_name

                # Check shared standards
                shared_standards = sorted(list(standards_a.intersection(set(s.upper() for s in rec_b.analysis.standards_mentioned))))
                if len(shared_standards) >= 1:
                    related_list.append({
                        "related_document_id": doc_id_b,
                        "related_file_name": name_b,
                        "relationship_type": "CITES_SAME_STANDARDS",
                        "shared_elements": shared_standards,
                        "similarity_score": min(1.0, len(shared_standards) * 0.4)
                    })

                # Check shared defects
                shared_defects = sorted(list(defects_a.intersection(set(d.lower() for d in rec_b.analysis.defects_mentioned))))
                if len(shared_defects) >= 1:
                    related_list.append({
                        "related_document_id": doc_id_b,
                        "related_file_name": name_b,
                        "relationship_type": "DISCUSSES_SAME_DEFECTS",
                        "shared_elements": shared_defects,
                        "similarity_score": min(1.0, len(shared_defects) * 0.35)
                    })

                # Check shared repair methods
                shared_repairs = sorted(list(repairs_a.intersection(set(r.lower() for r in rec_b.analysis.repair_methods))))
                if len(shared_repairs) >= 1:
                    related_list.append({
                        "related_document_id": doc_id_b,
                        "related_file_name": name_b,
                        "relationship_type": "DISCUSSES_SAME_REPAIR_METHODS",
                        "shared_elements": shared_repairs,
                        "similarity_score": min(1.0, len(shared_repairs) * 0.4)
                    })

                # Check shared topics
                shared_topics = sorted(list(topics_a.intersection(set(t.lower() for t in rec_b.analysis.main_topics))))
                if len(shared_topics) >= 2:
                    related_list.append({
                        "related_document_id": doc_id_b,
                        "related_file_name": name_b,
                        "relationship_type": "DISCUSSES_SAME_TOPICS",
                        "shared_elements": shared_topics,
                        "similarity_score": min(1.0, len(shared_topics) * 0.25)
                    })

            # Sort related documents by similarity score descending
            related_list.sort(key=lambda x: x["similarity_score"], reverse=True)

            results.append({
                "document_id": doc_id_a,
                "file_name": name_a,
                "title": rec_a.metadata.title,
                "category": rec_a.assigned_category,
                "related_documents": related_list[:15]  # Top 15 closest relationships
            })

        return results
