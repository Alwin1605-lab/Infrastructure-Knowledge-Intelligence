"""Document Organizer & Priority Ranking Service.

Organizes approved documents into exact building domain subcategories inside
`knowledge_base/`, routes rejected documents to `knowledge_base/rejected/`,
and assigns weighted priority ranks (Priority 1 to 5) based on `final_weighted_score`.
"""

import shutil
from pathlib import Path
from typing import Any

from app.core.logging import get_logger
from app.curation.models import CurationRecord, CurationStatus, DocumentType

logger = get_logger(__name__)


class DocumentOrganizer:
    """Categorizes documents into domain folders and ranks them by composite engineering priority."""

    def __init__(self, kb_root: str = "d:/Sem 7 Project/Project/knowledge_base"):
        self.kb_root = Path(kb_root)

    def organize_and_rank(self, records: list[CurationRecord], copy_files: bool = True) -> list[CurationRecord]:
        """Categorize, rank, and optionally copy files to destination folders.

        Returns:
            list[CurationRecord] sorted by priority rank ascending and weighted score descending.
        """
        # Create core directory structure
        categories = [
            "CPWD",
            "NBC",
            "Engineering_Books",
            "Research_Papers/Building_Maintenance",
            "Research_Papers/Structural_Health_Monitoring",
            "Research_Papers/Building_Defect_Detection",
            "Research_Papers/Building_Condition_Assessment",
            "Research_Papers/Predictive_Maintenance",
            "Research_Papers/Knowledge_Graph",
            "Research_Papers/RAG_LLM",
            "Research_Papers/Building_Rehabilitation",
            "Inspection_Reports",
            "Structural_Audit_Reports",
            "Building_Maintenance_Manuals",
            "rejected",
            "duplicates",
        ]

        for cat in categories:
            (self.kb_root / cat).mkdir(parents=True, exist_ok=True)

        # Assign Category and Priority Rank to each record
        for rec in records:
            if rec.status == CurationStatus.REJECTED.value:
                rec.assigned_category = "rejected"
                rec.priority_rank = 5
            elif rec.status == CurationStatus.DUPLICATE.value:
                rec.assigned_category = "duplicates"
                rec.priority_rank = 5
            else:
                rec.assigned_category = self._determine_category(rec)
                rec.priority_rank = self._determine_priority(rec)

            # Copy file to destination if requested and source exists
            if copy_files and Path(rec.metadata.source_path).exists():
                dest_dir = self.kb_root / rec.assigned_category
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest_path = dest_dir / rec.metadata.file_name
                try:
                    if not dest_path.exists():
                        shutil.copy2(rec.metadata.source_path, dest_path)
                except Exception as e:
                    logger.warning(f"Failed to copy file {rec.metadata.file_name} to {dest_dir}: {e}")

        # Sort all approved records cleanly
        records.sort(key=lambda r: (
            r.status != CurationStatus.APPROVED.value,
            r.priority_rank,
            -r.quality.final_weighted_score
        ))

        return records

    def _determine_category(self, rec: CurationRecord) -> str:
        """Route approved document into exact directory path based on content analysis and type."""
        doc_type = rec.metadata.document_type
        title_lower = rec.metadata.title.lower()
        text_summary = rec.analysis.summary.lower()
        topics = [t.lower() for t in rec.analysis.main_topics]

        if doc_type == DocumentType.CPWD_MANUAL.value or "cpwd" in title_lower:
            return "CPWD"
        if doc_type == DocumentType.NBC.value or "nbc" in title_lower or "national building" in title_lower:
            return "NBC"
        if doc_type == DocumentType.STRUCTURAL_AUDIT_REPORT.value or "audit" in title_lower:
            return "Structural_Audit_Reports"
        if doc_type == DocumentType.INSPECTION_REPORT.value or "inspection" in title_lower:
            return "Inspection_Reports"
        if doc_type == DocumentType.BUILDING_MAINTENANCE_MANUAL.value or "maintenance manual" in title_lower:
            return "Building_Maintenance_Manuals"
        if doc_type == DocumentType.ENGINEERING_BOOK.value or "book" in title_lower or "shetty" in title_lower:
            return "Engineering_Books"

        # Route Research Papers into specialized subcategories
        if doc_type == DocumentType.RESEARCH_PAPER.value or "research" in title_lower or "ijrar" in title_lower or "irjet" in title_lower:
            if any("knowledge graph" in t or "kg" in t for t in topics) or "knowledge graph" in text_summary:
                return "Research_Papers/Knowledge_Graph"
            if any("rag" in t or "llm" in t or "language model" in t for t in topics) or "rag" in text_summary:
                return "Research_Papers/RAG_LLM"
            if any("health monitoring" in t or "shm" in t or "upv" in t or "sensor" in t for t in topics) or "health monitoring" in text_summary:
                return "Research_Papers/Structural_Health_Monitoring"
            if any("predictive" in t or "forecasting" in t or "remaining useful life" in t for t in topics) or "predictive" in text_summary:
                return "Research_Papers/Predictive_Maintenance"
            if any("defect detection" in t or "crack classification" in t or "vision" in t or "yolo" in t or "cnn" in t for t in topics) or "defect" in text_summary:
                return "Research_Papers/Building_Defect_Detection"
            if any("rehabilitation" in t or "strengthening" in t or "jacketing" in t or "retrofitting" in t for t in topics) or "rehabilitation" in text_summary:
                return "Research_Papers/Building_Rehabilitation"
            if any("condition assessment" in t or "survey" in t for t in topics) or "condition assessment" in text_summary:
                return "Research_Papers/Building_Condition_Assessment"
            return "Research_Papers/Building_Maintenance"

        return "Building_Maintenance_Manuals"

    def _determine_priority(self, rec: CurationRecord) -> int:
        """Assign Priority Tier 1 to 5 based on composite weighted quality score and document type."""
        score = rec.quality.final_weighted_score
        doc_type = rec.metadata.document_type

        # Priority 1: Core foundation documents
        if doc_type in (DocumentType.CPWD_MANUAL.value, DocumentType.NBC.value) or score >= 85.0:
            return 1

        # Priority 2: High-impact research & core audit/inspection standards
        if doc_type in (DocumentType.STRUCTURAL_AUDIT_REPORT.value, DocumentType.RESEARCH_PAPER.value) and score >= 75.0:
            return 2

        # Priority 3: Detailed inspection reports & condition surveys
        if doc_type == DocumentType.INSPECTION_REPORT.value or score >= 65.0:
            return 3

        # Priority 4: Engineering books and supporting technical papers
        if doc_type == DocumentType.ENGINEERING_BOOK.value or score >= 55.0:
            return 4

        # Priority 5: Supporting guidelines and reference materials
        return 5
