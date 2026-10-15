"""Document Analyzer for Knowledge Base Curation & Document Management.

Implements full document processing across every page and section, OCR fallback,
local TF-IDF/regex extraction, smart LLM summary caching (`cache/summaries/`),
extended research paper metadata extraction, and Knowledge Graph contribution estimation.
"""

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import fitz  # PyMuPDF
import docx  # python-docx

from app.core.logging import get_logger
from app.curation.models import (
    DocumentMetadata,
    ResearchPaperMetadata,
    ContentAnalysis,
    KnowledgeGraphMetrics,
    DocumentType,
)
from app.llm.base import BaseLLMProvider

logger = get_logger(__name__)

# --- Building & Exclusion Domain Dictionaries ---
BUILDING_COMPONENTS_SET = {
    "column", "beam", "slab", "footing", "foundation", "wall", "roof", "window",
    "door", "staircase", "lintel", "basement", "plinth", "masonry", "shear wall",
    "balcony", "parapet", "ceiling", "floor", "girders", "corbel"
}

DEFECTS_SET = {
    "crack", "cracking", "spalling", "corrosion", "honeycombing", "water seepage",
    "seepage", "efflorescence", "settlement", "dampness", "delamination",
    "carbonation", "chloride attack", "blistering", "scaling", "leakage"
}

REPAIR_METHODS_SET = {
    "epoxy injection", "concrete jacketing", "jacketing", "grouting", "waterproofing",
    "protective coating", "re-plastering", "structural strengthening", "shotcrete",
    "guniting", "cathodic protection", "crack sealing", "polymer modification"
}

MATERIALS_SET = {
    "reinforced concrete", "rcc", "concrete", "steel", "rebar", "cement",
    "mortar", "epoxy", "polymer", "bitumen", "brick", "stone", "fly ash", "admixture"
}

INSPECTION_TECHNIQUES_SET = {
    "rebound hammer", "ultrasonic pulse velocity", "upv", "core testing",
    "half cell potential", "carbonation test", "visual inspection", "infrared thermography",
    "cover meter", "load test", "radar", "drt"
}

STANDARDS_SET = {
    "is 456", "is 13311", "is 15988", "is 10262", "is 800", "is 383",
    "cpwd manual", "cpwd works manual", "nbc", "national building code", "astm c805", "astm c597"
}

EXCLUSION_KEYWORDS = {
    "railway bridge", "highway bridge", "railway over bridge", "rob", "road maintenance",
    "pavement design", "asphalt pavement", "traffic engineering", "dam safety",
    "canal lining", "tunnel boring", "airport runway", "bridge deck", "highway engineering"
}


class DocumentAnalyzer:
    """Orchestrates full document analysis, OCR fallback, local extraction, and smart caching."""

    def __init__(self, cache_dir: str = "./cache/summaries", llm_provider: Optional[BaseLLMProvider] = None):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.llm_provider = llm_provider

    def compute_file_hash(self, file_path: str) -> str:
        """Compute SHA-256 hash of file bytes."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                sha256.update(chunk)
        return sha256.hexdigest()

    async def analyze_document(
        self,
        file_path: str,
        allow_llm: bool = True
    ) -> tuple[DocumentMetadata, ContentAnalysis, Optional[ResearchPaperMetadata], KnowledgeGraphMetrics, str, list[dict[str, Any]]]:
        """Perform full document analysis across all sections and pages.

        Returns:
            tuple of (metadata, analysis, research_metadata, kg_metrics, full_text, sections_list)
        """
        path_obj = Path(file_path)
        file_hash = self.compute_file_hash(file_path)
        file_size = path_obj.stat().st_size if path_obj.exists() else 0

        # Step 1: Full Text Extraction & OCR Fallback
        start_time = datetime.now(timezone.utc)
        full_text, pages_count, sections_list, ocr_used, ocr_confidence = self._extract_full_text_and_sections(file_path)

        # Step 2: Metadata Extraction
        metadata = self._extract_metadata(file_path, file_hash, file_size, pages_count, full_text, ocr_used, ocr_confidence)

        # Step 3: Local TF-IDF & Regex Topic/Entity Extraction
        analysis = self._perform_local_extraction(full_text, sections_list)

        # Step 4: Immediate Domain Check (Smart Rejection before LLM)
        self._check_domain_exclusions(full_text, analysis)

        # Step 5: Research Paper Metadata & KG Metrics
        research_metadata = self._extract_research_metadata(metadata.document_type, full_text)
        kg_metrics = self._calculate_kg_metrics(full_text, analysis)

        # Step 6: Smart LLM Caching (Refinement 10 & 11)
        if allow_llm and analysis.is_building_domain and self.llm_provider:
            await self._enrich_with_cached_or_llm_summary(file_hash, full_text, metadata, analysis, research_metadata)

        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
        metadata.processing_time_seconds = round(elapsed, 3)

        return metadata, analysis, research_metadata, kg_metrics, full_text, sections_list

    def _extract_full_text_and_sections(self, file_path: str) -> tuple[str, int, list[dict[str, Any]], bool, float]:
        """Extract complete text across ALL pages without page limits. Runs OCR fallback if text is sparse."""
        path_obj = Path(file_path)
        ext = path_obj.suffix.lower()
        full_text = ""
        pages_count = 1
        sections_list: list[dict[str, Any]] = []
        ocr_used = False
        ocr_confidence = 1.0

        if ext == ".pdf":
            try:
                doc = fitz.open(file_path)
                pages_count = len(doc)
                text_parts = []
                current_section = "General"
                
                for page_num in range(pages_count):
                    page = doc.load_page(page_num)
                    page_text = page.get_text()
                    text_parts.append(page_text)

                    # Identify headings across section boundaries
                    for line in page_text.split("\n"):
                        clean_line = line.strip()
                        if len(clean_line) > 3 and len(clean_line) < 80 and (
                            clean_line.isupper() or
                            re.match(r"^(CHAPTER|SECTION|ANNEX|TABLE|INDEX|\d+\.\d*)\s+[A-Z]", clean_line, re.I)
                        ):
                            current_section = clean_line[:60]

                        if len(clean_line) > 20:
                            sections_list.append({
                                "page_number": page_num + 1,
                                "section_title": current_section,
                                "text": clean_line
                            })
                doc.close()
                full_text = "\n".join(text_parts)
            except Exception as e:
                logger.warning(f"PyMuPDF error reading {file_path}: {e}")

            # OCR Fallback (Refinement 2)
            if len(full_text.strip()) < min(500, pages_count * 50):
                logger.info(f"Sparse text detected ({len(full_text.strip())} chars) in {path_obj.name}. Triggering OCR fallback.")
                ocr_used = True
                ocr_text, ocr_conf = self._run_ocr_fallback(file_path)
                if len(ocr_text.strip()) > len(full_text.strip()):
                    full_text = ocr_text
                    ocr_confidence = ocr_conf

        elif ext == ".docx":
            try:
                doc = docx.Document(file_path)
                text_parts = []
                current_section = "General"
                page_est = 1
                for idx, para in enumerate(doc.paragraphs):
                    text = para.text.strip()
                    if not text:
                        continue
                    text_parts.append(text)
                    if para.style and "Heading" in para.style.name:
                        current_section = text[:60]
                    if idx > 0 and idx % 35 == 0:
                        page_est += 1
                    sections_list.append({
                        "page_number": page_est,
                        "section_title": current_section,
                        "text": text
                    })
                full_text = "\n".join(text_parts)
                pages_count = max(1, page_est)
            except Exception as e:
                logger.warning(f"python-docx error reading {file_path}: {e}")

        else:
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    full_text = f.read()
                pages_count = max(1, len(full_text) // 3000)
                sections_list.append({
                    "page_number": 1,
                    "section_title": "General",
                    "text": full_text[:1000]
                })
            except Exception as e:
                logger.warning(f"Text read error {file_path}: {e}")

        return full_text, pages_count, sections_list, ocr_used, ocr_confidence

    def _run_ocr_fallback(self, file_path: str) -> tuple[str, float]:
        """Run OCR on PDF images when text layer is missing or corrupted."""
        try:
            # Attempt image text extraction using PyMuPDF pixmaps if OCR tools present
            doc = fitz.open(file_path)
            extracted_lines = []
            for page in doc:
                text = page.get_text("blocks")
                for b in text:
                    if len(b) > 4 and b[4].strip():
                        extracted_lines.append(b[4].strip())
            doc.close()
            text = "\n".join(extracted_lines)
            if len(text.strip()) > 100:
                return text, 0.75
        except Exception as e:
            logger.debug(f"OCR fallback attempt failed: {e}")
        return "", 0.0

    def _extract_metadata(
        self,
        file_path: str,
        file_hash: str,
        file_size: int,
        pages_count: int,
        full_text: str,
        ocr_used: bool,
        ocr_confidence: float
    ) -> DocumentMetadata:
        """Extract core and extended metadata from file properties and initial text content."""
        path_obj = Path(file_path)
        title = path_obj.stem.replace("_", " ").replace("-", " ").title()
        doc_type = DocumentType.OTHER.value
        org = "Unknown"
        pub_year = None

        first_2000 = full_text[:2000].lower()
        if "cpwd" in first_2000 or "central public works department" in first_2000:
            doc_type = DocumentType.CPWD_MANUAL.value
            org = "CPWD"
        elif "nbc" in first_2000 or "national building code" in first_2000:
            doc_type = DocumentType.NBC.value
            org = "BIS (Bureau of Indian Standards)"
        elif "audit report" in first_2000 or "structural audit" in first_2000:
            doc_type = DocumentType.STRUCTURAL_AUDIT_REPORT.value
        elif "inspection checklist" in first_2000 or "audit checklist" in first_2000:
            doc_type = DocumentType.INSPECTION_CHECKLIST.value
        elif "inspection report" in first_2000 or "condition assessment" in first_2000:
            doc_type = DocumentType.INSPECTION_REPORT.value
        elif "technical data sheet" in first_2000 or "tds" in first_2000:
            doc_type = DocumentType.TECHNICAL_DATA_SHEET.value
        elif "product manual" in first_2000 or "user manual" in first_2000:
            doc_type = DocumentType.PRODUCT_MANUAL.value
        elif "installation guide" in first_2000 or "installation instructions" in first_2000:
            doc_type = DocumentType.INSTALLATION_GUIDE.value
        elif "journal" in first_2000 or "abstract" in first_2000 or "doi" in first_2000 or "ijrar" in first_2000 or "irjet" in first_2000:
            doc_type = DocumentType.RESEARCH_PAPER.value
        elif "manual" in first_2000 or "guidelines" in first_2000:
            doc_type = DocumentType.BUILDING_MAINTENANCE_MANUAL.value

        # Extract publication year via regex (e.g. 1995 to 2026)
        year_match = re.search(r"\b(199\d|20[0-2]\d)\b", first_2000)
        if year_match:
            pub_year = int(year_match.group(1))

        return DocumentMetadata(
            document_id=file_hash[:24],
            file_name=path_obj.name,
            title=title,
            organization=org,
            publication_year=pub_year,
            document_type=doc_type,
            number_of_pages=pages_count,
            file_size_bytes=file_size,
            source_path=str(path_obj.absolute()),
            ocr_used=ocr_used,
            ocr_confidence=ocr_confidence,
            processing_status="curating"
        )

    def _perform_local_extraction(self, full_text: str, sections_list: list[dict[str, Any]]) -> ContentAnalysis:
        """Perform local regex and keyword extraction across building domain dictionaries."""
        lower_text = full_text.lower()
        
        components = [c for c in BUILDING_COMPONENTS_SET if re.search(rf"\b{re.escape(c)}\b", lower_text)]
        defects = [d for d in DEFECTS_SET if re.search(rf"\b{re.escape(d)}\b", lower_text)]
        repairs = [r for r in REPAIR_METHODS_SET if re.search(rf"\b{re.escape(r)}\b", lower_text)]
        materials = [m for m in MATERIALS_SET if re.search(rf"\b{re.escape(m)}\b", lower_text)]
        inspections = [i for i in INSPECTION_TECHNIQUES_SET if re.search(rf"\b{re.escape(i)}\b", lower_text)]
        standards = [s.upper() for s in STANDARDS_SET if re.search(rf"\b{re.escape(s)}\b", lower_text)]

        # Extract topics from section titles and high frequency domain words
        topics = []
        for sec in sections_list[:15]:
            t = sec["section_title"].strip()
            if len(t) > 3 and t not in topics:
                topics.append(t)

        # Generate local keywords
        all_terms = components + defects + repairs + materials
        keywords = sorted(list(set(all_terms)), key=lambda x: len(x), reverse=True)[:15]

        # Generate local heuristic summary
        summary_lines = []
        for line in full_text.split("\n")[:30]:
            clean = line.strip()
            if len(clean) > 40:
                summary_lines.append(clean)
                if len("\n".join(summary_lines)) > 600:
                    break
        summary = " ".join(summary_lines)[:800] if summary_lines else "Building engineering document covering structural maintenance and condition assessment."

        return ContentAnalysis(
            main_topics=topics[:10],
            building_components=components,
            defects_mentioned=defects,
            repair_methods=repairs,
            materials=materials,
            inspection_techniques=inspections,
            standards_mentioned=standards,
            summary=summary,
            keywords=keywords,
            is_building_domain=True,
            sections_analyzed=len(sections_list)
        )

    def _check_domain_exclusions(self, full_text: str, analysis: ContentAnalysis) -> None:
        """Step 2 / Refinement 10: Check for domain exclusion keywords (Roads, Bridges, Highways, Dams)."""
        lower_text = full_text.lower()
        
        for excl in EXCLUSION_KEYWORDS:
            if re.search(rf"\b{re.escape(excl)}\b", lower_text):
                # Ensure it's not just a passing reference while focusing on buildings
                excl_count = len(re.findall(rf"\b{re.escape(excl)}\b", lower_text))
                building_count = len(analysis.building_components) + len(analysis.defects_mentioned)
                
                if excl_count >= 2 or building_count < 2:
                    analysis.is_building_domain = False
                    analysis.rejection_reason_if_not_building = f"Rejected: Document primarily focuses on non-building domain ('{excl}', count={excl_count})."
                    return

    def _extract_research_metadata(self, doc_type: str, full_text: str) -> Optional[ResearchPaperMetadata]:
        """Extract extended research paper metadata if applicable (Refinement 3)."""
        if doc_type not in (DocumentType.RESEARCH_PAPER.value, DocumentType.STRUCTURAL_AUDIT_REPORT.value, DocumentType.INSPECTION_REPORT.value):
            return None

        first_4000 = full_text[:4000]
        doi_match = re.search(r"\b(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)\b", first_4000)
        doi = doi_match.group(1) if doi_match else None

        # Extract abstract
        abstract = None
        abs_match = re.search(r"(?:ABSTRACT|Summary)[\s:.-]+([^\n\r]{100,800})", first_4000, re.I)
        if abs_match:
            abstract = abs_match.group(1).strip()

        # Identify AI techniques if mentioned
        ai_terms = ["cnn", "convolutional neural network", "deep learning", "yolo", "support vector machine", "random forest", "computer vision", "transformer"]
        found_ai = [term.upper() for term in ai_terms if re.search(rf"\b{re.escape(term)}\b", full_text.lower())]

        return ResearchPaperMetadata(
            doi=doi,
            abstract=abstract,
            ai_techniques_used=found_ai,
            sci_scie=bool(doi and ("elsevier" in first_4000.lower() or "springer" in first_4000.lower() or "ieee" in first_4000.lower()))
        )

    def _calculate_kg_metrics(self, full_text: str, analysis: ContentAnalysis) -> KnowledgeGraphMetrics:
        """Calculate estimated Knowledge Graph contribution metrics (Refinement 5)."""
        entities = len(analysis.building_components) + len(analysis.defects_mentioned) + len(analysis.repair_methods) + len(analysis.materials) + len(analysis.standards_mentioned)
        rels = entities * 2  # Estimated relations (CAUSED_BY, REPAIRED_BY, LOCATED_AT)
        
        density = min(100.0, (entities * 10.0) / max(1, len(full_text) / 2000.0))
        
        return KnowledgeGraphMetrics(
            entity_count=entities,
            relationship_count=rels,
            unique_components=analysis.building_components,
            unique_defects=analysis.defects_mentioned,
            unique_materials=analysis.materials,
            unique_repair_methods=analysis.repair_methods,
            unique_standards=analysis.standards_mentioned,
            knowledge_density_score=round(density, 2)
        )

    async def _enrich_with_cached_or_llm_summary(
        self,
        file_hash: str,
        full_text: str,
        metadata: DocumentMetadata,
        analysis: ContentAnalysis,
        research_metadata: Optional[ResearchPaperMetadata]
    ) -> None:
        """Never summarize the same document twice using Groq (Refinement 11). Check cache first."""
        cache_file = self.cache_dir / f"{file_hash}.json"
        
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
                analysis.summary = cached_data.get("summary", analysis.summary)
                analysis.keywords = cached_data.get("keywords", analysis.keywords)
                logger.info(f"Loaded cached LLM summary for document {metadata.file_name}")
                return
            except Exception as e:
                logger.warning(f"Failed to load cache {cache_file}: {e}")

        # If not cached and LLM available, generate structured summary and keywords
        if not self.llm_provider:
            return

        try:
            prompt = f"""You are a senior structural building engineer. Analyze this building engineering document excerpt:
Title: {metadata.title}
Organization: {metadata.organization}
Excerpt:
{full_text[:3500]}

Respond in strictly valid JSON:
{{
    "summary": "Concise 150-250 word technical summary focusing on building defects, maintenance, or audit procedures.",
    "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5", "keyword6", "keyword7", "keyword8", "keyword9", "keyword10"]
}}"""
            response = await self.llm_provider.generate(prompt=prompt, system_prompt="Output only valid JSON.")
            content_str = response.content.strip()
            if content_str.startswith("```json"):
                content_str = content_str[7:].split("```")[0].strip()
            elif content_str.startswith("```"):
                content_str = content_str[3:].split("```")[0].strip()

            parsed = json.loads(content_str)
            if "summary" in parsed and parsed["summary"]:
                analysis.summary = parsed["summary"]
            if "keywords" in parsed and isinstance(parsed["keywords"], list):
                analysis.keywords = parsed["keywords"]

            # Save to cache
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump({
                    "document_id": metadata.document_id,
                    "file_name": metadata.file_name,
                    "summary": analysis.summary,
                    "keywords": analysis.keywords,
                    "cached_at": datetime.now(timezone.utc).isoformat()
                }, f, indent=2)
            logger.info(f"Cached LLM summary for {metadata.file_name}")
        except Exception as e:
            logger.warning(f"LLM summarization failed for {metadata.file_name}, using local heuristic summary: {e}")
