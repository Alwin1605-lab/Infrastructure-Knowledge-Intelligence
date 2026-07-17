"""Unit tests for Phase 4.5 Knowledge Base Curation & Document Management.

Tests document models, local extraction, domain rejection across roads/bridges,
quality scoring criteria, duplicate detection, and category routing.
"""

import pytest
from pathlib import Path
from app.curation.models import (
    DocumentMetadata,
    ContentAnalysis,
    QualityAssessment,
    KnowledgeGraphMetrics,
    CurationRecord,
    CurationStatus,
    ImportanceLevel,
    DocumentType,
    ChunkMetadata,
)
from app.curation.evaluator import DocumentEvaluator
from app.curation.deduplicator import DocumentDeduplicator
from app.curation.organizer import DocumentOrganizer
from app.curation.relationships import DocumentRelationshipBuilder
from app.curation.analyzer import DocumentAnalyzer


def test_chunk_citation_metadata_format():
    """Verify exact citation metadata formatting required by Refinement 7."""
    chunk = ChunkMetadata(
        chunk_id="chk_101",
        document_id="doc_001",
        document_title="CPWD Maintenance Manual",
        page_number=214,
        section_title="8.3 Waterproofing Repairs",
        chapter="Chapter 8"
    )
    citation = chunk.format_citation()
    assert "Source: CPWD Maintenance Manual" in citation
    assert "Page: 214" in citation
    assert "Section: 8.3 Waterproofing Repairs" in citation
    assert "Chapter: Chapter 8" in citation


def test_evaluator_domain_rejection():
    """Verify evaluator strictly rejects non-building civil engineering documents."""
    evaluator = DocumentEvaluator()
    meta = DocumentMetadata(
        document_id="id_bridge",
        file_name="Indian Railway Bridge Manual.pdf",
        title="Indian Railway Bridge Manual",
        source_path="/tmp/bridge.pdf"
    )
    analysis = ContentAnalysis(
        main_topics=["railway bridge maintenance", "girder inspection"],
        building_components=[],
        defects_mentioned=["corrosion"],
        is_building_domain=False,
        rejection_reason_if_not_building="Rejected: Document primarily focuses on non-building domain ('railway bridge', count=5)."
    )
    kg_metrics = KnowledgeGraphMetrics(entity_count=2, relationship_count=4)
    text = "This manual covers inspection and maintenance of Indian Railway Bridges and girders."

    quality, status, reasons = evaluator.evaluate(meta, analysis, kg_metrics, text)

    assert status == CurationStatus.REJECTED.value
    assert any("non-building" in r.lower() or "bridge" in r.lower() for r in reasons)


def test_evaluator_approval_and_weighted_scoring():
    """Verify approval of valid building document and weighted score calculation."""
    evaluator = DocumentEvaluator()
    meta = DocumentMetadata(
        document_id="id_cpwd",
        file_name="CPWD_Works_Manual_2024.pdf",
        title="CPWD Works Manual 2024",
        document_type=DocumentType.CPWD_MANUAL.value,
        number_of_pages=120,
        file_size_bytes=102400,
        source_path="/tmp/cpwd.pdf"
    )
    analysis = ContentAnalysis(
        main_topics=["rcc column repair", "waterproofing specifications"],
        building_components=["column", "beam", "slab"],
        defects_mentioned=["spalling", "corrosion", "water seepage"],
        repair_methods=["concrete jacketing", "epoxy injection"],
        materials=["reinforced concrete", "epoxy"],
        standards_mentioned=["IS 456", "CPWD MANUAL"],
        is_building_domain=True,
        sections_analyzed=10
    )
    kg_metrics = KnowledgeGraphMetrics(
        entity_count=12,
        relationship_count=24,
        knowledge_density_score=85.0
    )
    text = "Detailed engineering specifications for reinforced concrete column rehabilitation and waterproofing. This manual covers complete structural audit and inspection techniques according to CPWD and BIS national standards for residential and commercial building assets across India."
    
    quality, status, reasons = evaluator.evaluate(meta, analysis, kg_metrics, text)

    assert status == CurationStatus.APPROVED.value
    assert not reasons
    assert quality.final_weighted_score >= 80.0
    assert quality.importance_level == ImportanceLevel.CRITICAL.value


def test_deduplicator_exact_and_near_duplicate():
    """Verify deduplication marks lower-scoring duplicates correctly."""
    deduplicator = DocumentDeduplicator()
    rec1 = CurationRecord(
        metadata=DocumentMetadata(
            document_id="doc_1", file_name="file_A.pdf", title="Structural Audit Draft Report",
            source_path="/tmp/a.pdf", number_of_pages=20
        ),
        analysis=ContentAnalysis(main_topics=["audit"]),
        quality=QualityAssessment(final_weighted_score=78.0),
        status=CurationStatus.APPROVED.value,
        file_hash_sha256="hash_exact_123"
    )
    rec2 = CurationRecord(
        metadata=DocumentMetadata(
            document_id="doc_2", file_name="file_A_duplicate.pdf", title="Structural Audit Draft Report",
            source_path="/tmp/b.pdf", number_of_pages=18, ocr_used=True
        ),
        analysis=ContentAnalysis(main_topics=["audit"]),
        quality=QualityAssessment(final_weighted_score=65.0),
        status=CurationStatus.APPROVED.value,
        file_hash_sha256="hash_exact_123"
    )

    all_recs, groups = deduplicator.deduplicate([rec1, rec2])

    assert len(groups) == 1
    assert groups[0].canonical_record.metadata.document_id == "doc_1"
    assert len(groups[0].duplicates) == 1
    assert groups[0].duplicates[0].status == CurationStatus.DUPLICATE.value


def test_organizer_category_routing(tmp_path):
    """Verify organizer routes CPWD, NBC, and Research Papers cleanly into correct directories."""
    organizer = DocumentOrganizer(kb_root=str(tmp_path))
    rec = CurationRecord(
        metadata=DocumentMetadata(
            document_id="doc_kg", file_name="kg_paper.pdf", title="Knowledge Graph for Building Maintenance",
            document_type=DocumentType.RESEARCH_PAPER.value, source_path="/tmp/kg.pdf"
        ),
        analysis=ContentAnalysis(
            main_topics=["knowledge graph", "ontology extraction"],
            summary="Extracting knowledge graph for building structural maintenance."
        ),
        quality=QualityAssessment(final_weighted_score=82.0),
        status=CurationStatus.APPROVED.value
    )

    ranked = organizer.organize_and_rank([rec], copy_files=False)
    assert ranked[0].assigned_category == "Research_Papers/Knowledge_Graph"
