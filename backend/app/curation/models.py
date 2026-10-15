"""Pydantic data models for Knowledge Base Curation & Document Management.

Defines schemas for document metadata, research paper metadata, content analysis,
quality assessment, priority scoring, KG contributions, chunk/citation metadata,
and curation records.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator


class DocumentType(str, Enum):
    """Canonical document types supported in the Building Knowledge Base."""
    CPWD_MANUAL = "CPWD Manual"
    NBC = "NBC"
    ENGINEERING_BOOK = "Engineering Book"
    RESEARCH_PAPER = "Research Paper"
    INSPECTION_REPORT = "Inspection Report"
    STRUCTURAL_AUDIT_REPORT = "Structural Audit Report"
    BUILDING_MAINTENANCE_MANUAL = "Building Maintenance Manual"
    TECHNICAL_DATA_SHEET = "Technical Data Sheet"
    PRODUCT_MANUAL = "Product Manual"
    INSTALLATION_GUIDE = "Installation Guide"
    INSPECTION_CHECKLIST = "Inspection Checklist"
    OTHER = "Other"


class ImportanceLevel(str, Enum):
    """Overall importance tier assigned during quality evaluation."""
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class CurationStatus(str, Enum):
    """Status of a document through the curation pipeline."""
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DUPLICATE = "DUPLICATE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class DocumentMetadata(BaseModel):
    """Core and extended metadata for an engineering document."""
    document_id: str = Field(..., description="Unique identifier or hash of the document.")
    file_name: str = Field(..., description="Original file basename.")
    title: str = Field(..., description="Document title or extracted header.")
    authors: list[str] = Field(default_factory=list, description="Authors or contributing engineers.")
    organization: str = Field(default="Unknown", description="Publishing organization (e.g. CPWD, BIS, IIT).")
    publication_year: Optional[int] = Field(default=None, description="Year of publication.")
    document_type: str = Field(default=DocumentType.OTHER.value, description="Assigned DocumentType.")
    source_url: Optional[str] = Field(default=None, description="Source URL or repository reference.")
    number_of_pages: int = Field(default=1, description="Total number of pages in the document.")
    language: str = Field(default="en", description="Language code of the document.")
    file_size_bytes: int = Field(default=0, description="Size of the document file in bytes.")
    source_path: str = Field(..., description="Absolute path to the source file.")

    # Extended Document Metadata (Refinement 4)
    document_version: str = Field(default="1.0", description="Version of the document.")
    curation_date: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO timestamp of when curation was performed."
    )
    pipeline_version: str = Field(default="4.5", description="Version of the curation engine.")
    ocr_used: bool = Field(default=False, description="Whether OCR fallback was required to extract text.")
    ocr_confidence: float = Field(default=1.0, description="Estimated confidence of OCR text extraction (0.0 to 1.0).")
    processing_time_seconds: float = Field(default=0.0, description="Seconds taken to process and analyze this document.")
    processing_status: str = Field(default="curated", description="Current processing lifecycle status.")


class ResearchPaperMetadata(BaseModel):
    """Extended metadata extracted specifically from academic or industrial research papers."""
    journal_name: Optional[str] = Field(default=None, description="Name of the academic journal or conference.")
    publisher: Optional[str] = Field(default=None, description="Publisher name (e.g. Springer, IEEE, Elsevier).")
    publication_year: Optional[int] = Field(default=None, description="Publication year.")
    doi: Optional[str] = Field(default=None, description="Digital Object Identifier.")
    sci_scie: bool = Field(default=False, description="Whether the journal is SCI/SCIE indexed.")
    abstract: Optional[str] = Field(default=None, description="Paper abstract.")
    research_problem: Optional[str] = Field(default=None, description="Specific engineering problem addressed.")
    research_gap: Optional[str] = Field(default=None, description="Identified gap in current building engineering literature.")
    methodology: Optional[str] = Field(default=None, description="Experimental or computational methodology.")
    ai_techniques_used: list[str] = Field(default_factory=list, description="AI/ML or computer vision techniques used.")
    dataset_used: Optional[str] = Field(default=None, description="Dataset utilized for evaluation.")
    evaluation_metrics: list[str] = Field(default_factory=list, description="Metrics used (accuracy, F1, RMSE, etc.).")
    results_summary: Optional[str] = Field(default=None, description="Key empirical findings.")
    limitations: Optional[str] = Field(default=None, description="Noted study limitations.")
    future_work: Optional[str] = Field(default=None, description="Suggested directions for future research.")


class KnowledgeGraphMetrics(BaseModel):
    """Metrics estimating how much ontology contribution this document makes to the Building KG."""
    entity_count: int = Field(default=0, description="Estimated number of building entities extracted.")
    relationship_count: int = Field(default=0, description="Estimated number of relationships extracted.")
    unique_components: list[str] = Field(default_factory=list, description="Unique building components identified.")
    unique_defects: list[str] = Field(default_factory=list, description="Unique structural or architectural defects identified.")
    unique_materials: list[str] = Field(default_factory=list, description="Unique building materials identified.")
    unique_repair_methods: list[str] = Field(default_factory=list, description="Unique repair or restoration methods identified.")
    unique_standards: list[str] = Field(default_factory=list, description="Unique building codes or standards cited.")
    knowledge_density_score: float = Field(default=0.0, description="Normalized knowledge density score (0 to 100).")


class ChunkMetadata(BaseModel):
    """Structured metadata attached to every vector chunk during indexing and RAG retrieval."""
    chunk_id: str = Field(..., description="Unique identifier for the chunk.")
    document_id: str = Field(..., description="ID of the parent document.")
    document_title: str = Field(..., description="Title of the parent document.")
    page_number: int = Field(default=1, description="Page number where this chunk originated.")
    section_title: str = Field(default="General", description="Section or chapter title.")
    chapter: str = Field(default="", description="Chapter number or name.")
    priority: int = Field(default=3, description="Priority ranking of the parent document (1 to 5).")
    category: str = Field(default="CPWD", description="Assigned knowledge base category.")
    heading: str = Field(default="", description="Immediate heading above this chunk.")
    source_type: str = Field(default="Manual", description="Document type.")
    paragraph: int = Field(default=1, description="Paragraph index inside the section.")

    def format_citation(self) -> str:
        """Format chunk location as an exact engineering citation string."""
        lines = [f"Source: {self.document_title}"]
        if self.page_number > 0:
            lines.append(f"Page: {self.page_number}")
        if self.section_title and self.section_title != "General":
            lines.append(f"Section: {self.section_title}")
        elif self.heading:
            lines.append(f"Heading: {self.heading}")
        if self.chapter:
            lines.append(f"Chapter: {self.chapter}")
        return "\n".join(lines)


class ContentAnalysis(BaseModel):
    """Results of full document topic, entity, and domain extraction."""
    main_topics: list[str] = Field(default_factory=list, description="Primary topics discussed.")
    building_components: list[str] = Field(default_factory=list, description="Building structural/architectural components mentioned.")
    defects_mentioned: list[str] = Field(default_factory=list, description="Defects or deterioration modes mentioned.")
    repair_methods: list[str] = Field(default_factory=list, description="Rehabilitation, repair, and waterproofing methods.")
    materials: list[str] = Field(default_factory=list, description="Construction and repair materials mentioned.")
    inspection_techniques: list[str] = Field(default_factory=list, description="NDT or visual inspection techniques mentioned.")
    standards_mentioned: list[str] = Field(default_factory=list, description="IS, CPWD, NBC, or ASTM standards cited.")
    ai_techniques: list[str] = Field(default_factory=list, description="AI/ML models or vision algorithms discussed.")
    building_systems: list[str] = Field(default_factory=list, description="MEP, HVAC, drainage, or structural systems.")
    structural_elements: list[str] = Field(default_factory=list, description="Specific RCC or masonry structural elements.")
    summary: str = Field(default="", description="Concise summary (150 to 300 words).")
    keywords: list[str] = Field(default_factory=list, description="10 to 20 descriptive keywords.")
    is_building_domain: bool = Field(default=True, description="Whether the document belongs strictly to building engineering.")
    rejection_reason_if_not_building: Optional[str] = Field(default=None, description="Reason if rejected due to non-building domain.")
    sections_analyzed: int = Field(default=0, description="Total number of sections processed during full analysis.")


class QualityAssessment(BaseModel):
    """Detailed multi-criteria engineering quality evaluation and weighted priority score."""
    domain_relevance: float = Field(default=100.0, description="Score 0-100 for relevance to RCC & building engineering.")
    technical_depth: float = Field(default=80.0, description="Score 0-100 for technical rigor and engineering specifications.")
    engineering_value: float = Field(default=80.0, description="Score 0-100 for actionable engineering guidance.")
    maintenance_knowledge: float = Field(default=75.0, description="Score 0-100 for building maintenance depth.")
    inspection_knowledge: float = Field(default=75.0, description="Score 0-100 for inspection and audit techniques.")
    repair_knowledge: float = Field(default=75.0, description="Score 0-100 for concrete and masonry repair methods.")
    building_focus: float = Field(default=100.0, description="Score 0-100 for exclusive focus on building assets vs infrastructure.")
    ai_contribution: float = Field(default=0.0, description="Score 0-100 for AI/ML methodology contribution (for research papers).")
    knowledge_graph_value: float = Field(default=80.0, description="Score 0-100 estimating richness of extractable entities/relationships.")
    rag_value: float = Field(default=85.0, description="Score 0-100 estimating utility as a RAG vector retrieval source.")
    
    # Composite and Weighted Scores (Refinement 12)
    overall_quality_score: float = Field(default=80.0, description="Simple average across core quality criteria.")
    knowledge_density: float = Field(default=80.0, description="Normalized density of actionable facts per page.")
    engineering_importance: float = Field(default=85.0, description="Composite engineering and maintenance value.")
    rag_importance: float = Field(default=85.0, description="Utility weighting for RAG query answering.")
    kg_importance: float = Field(default=80.0, description="Utility weighting for graph enrichment.")
    final_weighted_score: float = Field(default=82.0, description="Final weighted score used for priority ranking.")
    importance_level: str = Field(default=ImportanceLevel.HIGH.value, description="Assigned ImportanceLevel.")


class CurationRecord(BaseModel):
    """Consolidated record representing a single document's entire curation journey."""
    metadata: DocumentMetadata
    research_metadata: Optional[ResearchPaperMetadata] = None
    kg_metrics: KnowledgeGraphMetrics = Field(default_factory=KnowledgeGraphMetrics)
    analysis: ContentAnalysis
    quality: QualityAssessment
    status: str = Field(default=CurationStatus.APPROVED.value, description="Assigned CurationStatus.")
    rejection_reasons: list[str] = Field(default_factory=list, description="Specific reasons if rejected.")
    assigned_category: str = Field(default="CPWD", description="Assigned subdirectory folder path.")
    priority_rank: int = Field(default=3, description="Assigned Priority 1 to 5.")
    file_hash_sha256: str = Field(default="", description="SHA-256 hash of original file bytes.")

    @property
    def is_approved(self) -> bool:
        """Check if document passed curation."""
        return self.status == CurationStatus.APPROVED.value


class DuplicateGroup(BaseModel):
    """Groups exact or near-duplicate documents, retaining the canonical version."""
    canonical_record: CurationRecord
    duplicates: list[CurationRecord] = Field(default_factory=list)
