"""End-to-End Curation Pipeline Runner (Phase 4.5).

Orchestrates document discovery, full text analysis, OCR fallback, domain filtering,
quality scoring, duplicate detection, categorization, priority ranking, and report generation.

Usage:
    python -m app.curation.run_curation --source "d:/Sem 7 Project/data" --dest "d:/Sem 7 Project/Project/knowledge_base" --no-llm
"""

import argparse
import asyncio
from pathlib import Path
from typing import Optional, Any

from app.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.curation.analyzer import DocumentAnalyzer
from app.curation.evaluator import DocumentEvaluator
from app.curation.deduplicator import DocumentDeduplicator
from app.curation.organizer import DocumentOrganizer
from app.curation.relationships import DocumentRelationshipBuilder
from app.curation.reporter import CurationReporter
from app.curation.models import CurationRecord, CurationStatus
from app.llm.factory import create_llm_provider

logger = get_logger(__name__)


async def run_curation_pipeline(
    source_dir: str = "d:/Sem 7 Project/data",
    dest_dir: str = "d:/Sem 7 Project/Project/knowledge_base",
    allow_llm: bool = False,
    copy_files: bool = True
) -> dict[str, Any]:
    """Execute the full 10-step Knowledge Base Curation & Document Management pipeline."""
    logger.info(f"Starting Phase 4.5 Curation Pipeline across {source_dir} -> {dest_dir}")

    # Initialize components
    settings = get_settings()
    llm_provider = None
    if allow_llm and settings.GROQ_API_KEY and settings.GROQ_API_KEY != "test_key_not_real":
        try:
            llm_provider = create_llm_provider(settings)
            logger.info("Initialized Groq LLM provider for smart summarization.")
        except Exception as e:
            logger.warning(f"Could not initialize LLM provider, using local/cached extraction: {e}")

    analyzer = DocumentAnalyzer(cache_dir="./cache/summaries", llm_provider=llm_provider)
    evaluator = DocumentEvaluator()
    deduplicator = DocumentDeduplicator()
    organizer = DocumentOrganizer(kb_root=dest_dir)
    relationship_builder = DocumentRelationshipBuilder()
    reporter = CurationReporter(kb_root=dest_dir)

    # Step 1: Document Discovery
    source_path = Path(source_dir)
    if not source_path.exists():
        raise FileNotFoundError(f"Source directory not found: {source_dir}")

    file_paths = []
    for ext in ("*.pdf", "*.docx", "*.txt"):
        file_paths.extend(list(source_path.rglob(ext)))

    logger.info(f"Discovered {len(file_paths)} candidate documents in {source_dir}")

    records: list[CurationRecord] = []

    # Steps 2 & 3 & 5: Content Analysis, Quality Assessment, Domain Filtering
    for idx, fp in enumerate(file_paths, 1):
        try:
            logger.debug(f"[{idx}/{len(file_paths)}] Analyzing {fp.name}...")
            meta, analysis, res_meta, kg_metrics, full_text, _ = await analyzer.analyze_document(
                str(fp.absolute()), allow_llm=allow_llm
            )
            meta.file_size_bytes = fp.stat().st_size
            meta.file_name = fp.name

            # Evaluate quality and check domain rejection
            quality, status, rejection_reasons = evaluator.evaluate(
                meta, analysis, kg_metrics, full_text, res_meta
            )
            meta.processing_status = status.lower()

            rec = CurationRecord(
                metadata=meta,
                research_metadata=res_meta,
                kg_metrics=kg_metrics,
                analysis=analysis,
                quality=quality,
                status=status,
                rejection_reasons=rejection_reasons,
                file_hash_sha256=analyzer.compute_file_hash(str(fp.absolute()))
            )
            records.append(rec)
        except Exception as e:
            logger.error(f"Failed to process candidate file {fp}: {e}", exc_info=True)

    # Step 4: Duplicate Detection
    records, duplicate_groups = deduplicator.deduplicate(records)

    # Step 6 & 7: Categorization and Priority Ranking
    records = organizer.organize_and_rank(records, copy_files=copy_files)

    # Step 13: Document Relationships
    relationships = relationship_builder.build_relationships(records)

    # Step 8, 9, 15: Generate all 8 reports and JSON databases
    report_paths = reporter.generate_all_reports(records, duplicate_groups, relationships)

    approved_count = sum(1 for r in records if r.status == CurationStatus.APPROVED.value)
    rejected_count = sum(1 for r in records if r.status == CurationStatus.REJECTED.value)
    duplicate_count = sum(1 for r in records if r.status == CurationStatus.DUPLICATE.value)

    summary = {
        "total_scanned": len(records),
        "approved": approved_count,
        "rejected": rejected_count,
        "duplicates": duplicate_count,
        "reports_generated": report_paths
    }
    logger.info(f"Phase 4.5 Curation Pipeline completed: {approved_count} approved, {rejected_count} rejected, {duplicate_count} duplicates.")
    return summary


def main():
    parser = argparse.ArgumentParser(description="Run Phase 4.5 Knowledge Base Curation Pipeline")
    parser.add_argument("--source", default="d:/Sem 7 Project/data", help="Source data directory")
    parser.add_argument("--dest", default="d:/Sem 7 Project/Project/knowledge_base", help="Destination knowledge base root")
    parser.add_argument("--allow-llm", action="store_true", help="Enable Groq LLM for smart summarization")
    parser.add_argument("--no-copy", action="store_true", help="Do not copy physical files, only generate reports")
    args = parser.parse_args()

    setup_logging(debug=True)
    asyncio.run(run_curation_pipeline(
        source_dir=args.source,
        dest_dir=args.dest,
        allow_llm=args.allow_llm,
        copy_files=not args.no_copy
    ))


if __name__ == "__main__":
    main()
