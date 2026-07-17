"""Knowledge Base Curation & Document Management Engine (Phase 4.5).

Orchestrates automated document discovery, full text analysis, OCR fallback,
domain validation, quality assessment, deduplication, categorization, priority ranking,
and knowledge coverage reporting for the Building Knowledge Intelligence System.

Domain: Strictly Buildings Only (RCC, Residential, Commercial, Institutional, Government).
Rejects non-building civil engineering documents (Roads, Bridges, Highways, Dams, Railways).
"""

from app.curation.models import (
    DocumentMetadata,
    ResearchPaperMetadata,
    ContentAnalysis,
    QualityAssessment,
    CurationRecord,
    DuplicateGroup,
    KnowledgeGraphMetrics,
    ChunkMetadata,
)
from app.curation.analyzer import DocumentAnalyzer
from app.curation.evaluator import DocumentEvaluator
from app.curation.deduplicator import DocumentDeduplicator
from app.curation.organizer import DocumentOrganizer
from app.curation.relationships import DocumentRelationshipBuilder
from app.curation.reporter import CurationReporter

__all__ = [
    "DocumentMetadata",
    "ResearchPaperMetadata",
    "ContentAnalysis",
    "QualityAssessment",
    "CurationRecord",
    "DuplicateGroup",
    "KnowledgeGraphMetrics",
    "ChunkMetadata",
    "DocumentAnalyzer",
    "DocumentEvaluator",
    "DocumentDeduplicator",
    "DocumentOrganizer",
    "DocumentRelationshipBuilder",
    "CurationReporter",
]
