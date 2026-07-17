"""Document Quality Assessment & Domain Rejection Evaluator.

Implements multi-criteria engineering scoring (`overall_quality_score`, `knowledge_density`,
`engineering_importance`, `rag_importance`, `kg_importance`, `final_weighted_score`),
strict building domain rejection (Roads, Bridges, Highways, Dams), and importance categorization.
"""

from typing import Optional
from app.core.logging import get_logger
from app.curation.models import (
    DocumentMetadata,
    ContentAnalysis,
    QualityAssessment,
    KnowledgeGraphMetrics,
    ResearchPaperMetadata,
    CurationStatus,
    ImportanceLevel,
    DocumentType,
)

logger = get_logger(__name__)


class DocumentEvaluator:
    """Evaluates document quality across 10 engineering criteria and performs strict domain filtering."""

    def evaluate(
        self,
        metadata: DocumentMetadata,
        analysis: ContentAnalysis,
        kg_metrics: KnowledgeGraphMetrics,
        full_text: str,
        research_metadata: Optional[ResearchPaperMetadata] = None
    ) -> tuple[QualityAssessment, str, list[str]]:
        """Evaluate a document and decide its approval status and rejection reasons.

        Returns:
            tuple of (quality_assessment, status_string, rejection_reasons_list)
        """
        rejection_reasons = []

        # Check Step 5 Rejection Boundaries First
        if not analysis.is_building_domain:
            reason = analysis.rejection_reason_if_not_building or "Document primarily focuses on non-building infrastructure."
            rejection_reasons.append(reason)

        if metadata.file_size_bytes == 0 or len(full_text.strip()) == 0:
            rejection_reasons.append("Rejected: Document is empty or contains zero extractable text.")

        if metadata.ocr_used and metadata.ocr_confidence < 0.35:
            rejection_reasons.append(f"Rejected: Extremely poor OCR quality (confidence={metadata.ocr_confidence:.2f}).")

        if len(full_text.strip()) < 150:
            rejection_reasons.append("Rejected: Document text length is critically short (<150 characters).")

        # Calculate Individual Quality Scores (0 to 100)
        domain_relevance = 100.0 if analysis.is_building_domain else 10.0
        building_focus = 100.0 if analysis.is_building_domain else 15.0

        # Technical depth based on standards, exact measurements, and sections
        tech_depth = min(100.0, 40.0 + len(analysis.standards_mentioned) * 15.0 + min(40.0, analysis.sections_analyzed * 4.0))
        if metadata.document_type in (DocumentType.CPWD_MANUAL.value, DocumentType.NBC.value):
            tech_depth = max(tech_depth, 90.0)

        # Maintenance, inspection, and repair knowledge
        maint_know = min(100.0, 30.0 + len(analysis.repair_methods) * 15.0 + len(analysis.defects_mentioned) * 10.0)
        if metadata.document_type in (DocumentType.BUILDING_MAINTENANCE_MANUAL.value, DocumentType.CPWD_MANUAL.value):
            maint_know = max(maint_know, 85.0)

        insp_know = min(100.0, 30.0 + len(analysis.inspection_techniques) * 20.0 + len(analysis.defects_mentioned) * 10.0)
        if metadata.document_type in (DocumentType.INSPECTION_REPORT.value, DocumentType.STRUCTURAL_AUDIT_REPORT.value):
            insp_know = max(insp_know, 88.0)

        repair_know = min(100.0, 30.0 + len(analysis.repair_methods) * 20.0 + len(analysis.materials) * 10.0)
        if "repair" in metadata.file_name.lower() or "rehabilitation" in metadata.file_name.lower():
            repair_know = max(repair_know, 90.0)

        eng_val = (tech_depth + maint_know + insp_know + repair_know) / 4.0

        # AI contribution (especially for research papers)
        ai_contrib = 0.0
        if research_metadata and research_metadata.ai_techniques_used:
            ai_contrib = min(100.0, len(research_metadata.ai_techniques_used) * 30.0)
        elif len(analysis.ai_techniques) > 0:
            ai_contrib = min(100.0, len(analysis.ai_techniques) * 25.0)

        # KG and RAG utility
        kg_val = min(100.0, (kg_metrics.entity_count * 5.0) + (kg_metrics.relationship_count * 2.0))
        rag_val = min(100.0, (domain_relevance * 0.5) + (tech_depth * 0.3) + min(20.0, metadata.number_of_pages * 2.0))

        # Composite Scores (Refinement 12)
        overall = round((domain_relevance + tech_depth + eng_val + maint_know + insp_know + repair_know + building_focus + kg_val + rag_val) / 9.0, 2)
        know_density = kg_metrics.knowledge_density_score
        eng_importance = round((eng_val * 0.4) + (tech_depth * 0.3) + (maint_know * 0.15) + (repair_know * 0.15), 2)
        rag_importance = round((rag_val * 0.5) + (domain_relevance * 0.3) + (building_focus * 0.2), 2)
        kg_importance = round((kg_val * 0.6) + (know_density * 0.4), 2)

        final_weighted = round(0.35 * overall + 0.25 * eng_importance + 0.20 * rag_importance + 0.20 * kg_importance, 2)

        # Check minimum engineering knowledge boundary
        if kg_metrics.entity_count == 0 and final_weighted < 30.0 and not rejection_reasons:
            rejection_reasons.append("Rejected: Document contains almost no building engineering or structural knowledge.")

        # Determine Importance Level
        if final_weighted >= 85.0 or metadata.document_type in (DocumentType.CPWD_MANUAL.value, DocumentType.NBC.value):
            importance = ImportanceLevel.CRITICAL.value
        elif final_weighted >= 72.0:
            importance = ImportanceLevel.HIGH.value
        elif final_weighted >= 55.0:
            importance = ImportanceLevel.MEDIUM.value
        else:
            importance = ImportanceLevel.LOW.value

        quality = QualityAssessment(
            domain_relevance=round(domain_relevance, 2),
            technical_depth=round(tech_depth, 2),
            engineering_value=round(eng_val, 2),
            maintenance_knowledge=round(maint_know, 2),
            inspection_knowledge=round(insp_know, 2),
            repair_knowledge=round(repair_know, 2),
            building_focus=round(building_focus, 2),
            ai_contribution=round(ai_contrib, 2),
            knowledge_graph_value=round(kg_val, 2),
            rag_value=round(rag_val, 2),
            overall_quality_score=overall,
            knowledge_density=know_density,
            engineering_importance=eng_importance,
            rag_importance=rag_importance,
            kg_importance=kg_importance,
            final_weighted_score=final_weighted,
            importance_level=importance
        )

        status = CurationStatus.REJECTED.value if rejection_reasons else CurationStatus.APPROVED.value

        return quality, status, rejection_reasons
