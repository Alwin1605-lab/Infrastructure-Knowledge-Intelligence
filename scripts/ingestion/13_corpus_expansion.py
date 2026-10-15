#!/usr/bin/env python3
"""
Phase 13 — Corpus Expansion Script
====================================
Task: Recover LEDG (KG stage only) and process acquired_documents through
the legitimate production pipeline.

Rules:
  - NEVER manually set status to completed
  - NEVER skip ChromaDB / Neo4j pipeline stages
  - NEVER fabricate entities, chunks, or metadata
  - A document is only COMPLETED when all pipeline stages genuinely succeed
  - Failures are reported precisely; processing continues for other docs
  - Groq rate limits use exponential backoff from the KGBuilder._extract_with_retry

Pipeline used:
  1. For LEDG: KG-only resume (embeddings already present)
  2. For acquired_documents:
       a. Download PDF from pdf_url (try multiple strategies)
       b. Validate PDF (must have real text, >1 page, >5000 bytes)
       c. Run full pipeline: extract -> chunk -> embed -> KG
       d. Update AcquiredDocument.status to INDEXED on success
"""

import asyncio
import sys
import os
import json
import time
import datetime
import hashlib
import traceback
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap: add backend to sys.path so production app imports work
# ---------------------------------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))
os.chdir(BACKEND_DIR)  # .env is read relative to cwd

OUTPUT_DIR = Path("../experiments/v3")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Helper: Initialize the Beanie ODM + all services exactly as app.main does
# ---------------------------------------------------------------------------
async def init_services():
    from app.config import get_settings
    from app.db.connection import init_db
    from app.vectorstore.connection import init_vectorstore
    from app.knowledge_graph.connection import init_kg
    from app.embedding import HuggingFaceEmbeddingService
    from app.llm import create_llm_provider
    from app.vectorstore.indexer import ChromaIndexer
    from app.knowledge_graph.builder import KGBuilder

    settings = get_settings()

    # MongoDB + Beanie
    await init_db(settings)

    # ChromaDB
    await init_vectorstore(settings)

    # Neo4j
    await init_kg(settings)

    # Embedding
    embedding_svc = HuggingFaceEmbeddingService(settings)

    # LLM
    llm_provider = create_llm_provider(settings)

    # Indexer + KG builder
    indexer = ChromaIndexer(embedding_service=embedding_svc)
    kg_builder = KGBuilder(llm_provider=llm_provider)

    return settings, indexer, kg_builder


# ---------------------------------------------------------------------------
# Helper: Robust PDF download with multiple fallback strategies
# ---------------------------------------------------------------------------
async def download_pdf(pdf_url: str, target_path: str) -> tuple[bool, str]:
    """
    Try to download a real PDF from the given URL.
    Returns (success, reason).
    Validates that the downloaded file is a genuine PDF with text content.
    """
    import httpx
    import fitz  # PyMuPDF

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/pdf,*/*",
    }

    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=60.0,
            headers=headers,
        ) as client:
            resp = await client.get(pdf_url)

            if resp.status_code != 200:
                return False, f"HTTP {resp.status_code}"

            content = resp.content
            if len(content) < 5000:
                return False, f"File too small ({len(content)} bytes) — likely not a real PDF"

            # Write to disk
            with open(target_path, "wb") as f:
                f.write(content)

            # Validate: must open as PDF and have text
            try:
                doc = fitz.open(target_path)
                page_count = doc.page_count
                if page_count < 1:
                    doc.close()
                    os.remove(target_path)
                    return False, "PDF has 0 pages"

                # Extract text from first few pages
                text = ""
                for p_i in range(min(3, page_count)):
                    text += doc[p_i].get_text()
                doc.close()

                if len(text.strip()) < 200:
                    os.remove(target_path)
                    return False, f"PDF has {page_count} pages but very little text ({len(text.strip())} chars) — likely a bot-challenge page"

                return True, f"OK ({page_count} pages, {len(content)} bytes)"

            except Exception as pdf_err:
                if os.path.exists(target_path):
                    os.remove(target_path)
                return False, f"PDF validation failed: {pdf_err}"

    except Exception as exc:
        return False, f"Download error: {exc}"


# ---------------------------------------------------------------------------
# Stage 1: Recover LEDG (KG stage only)
# ---------------------------------------------------------------------------
async def recover_ledg_kg(settings, kg_builder) -> dict:
    """
    LEDG has 237 ChromaDB chunks already. Only the KG stage failed.
    Resume from KG stage without re-embedding.
    """
    from app.models.document import Document, DocumentStatus
    from app.models.processing_job import ProcessingJob, JobStatus, JobStep
    from bson import ObjectId

    LEDG_DOC_ID = "6a7812eed03ebe1c6f5851dc"

    result = {
        "document_id": LEDG_DOC_ID,
        "filename": "0-LEDG-v.1.0-120224.pdf",
        "stage": "kg_recovery",
        "success": False,
        "kg_entities": 0,
        "kg_relationships": 0,
        "error": "",
        "duration_seconds": 0.0,
    }

    start = time.time()
    print(f"\n[LEDG RECOVERY] Starting KG recovery for 0-LEDG-v.1.0-120224.pdf")

    try:
        doc = await Document.get(ObjectId(LEDG_DOC_ID))
        if doc is None:
            result["error"] = "Document not found in MongoDB"
            return result

        print(f"  Current status: {doc.status}")
        print(f"  Pages in MongoDB: {len(doc.pages)}")
        print(f"  full_text length: {len(doc.full_text or '')}")

        if not doc.pages:
            result["error"] = "Document has no extracted pages in MongoDB — cannot resume KG"
            return result

        # Find or create a ProcessingJob for resumption
        existing_job = await ProcessingJob.find_one({"document_id": LEDG_DOC_ID})
        if existing_job is None:
            job = ProcessingJob(
                document_id=LEDG_DOC_ID,
                filename=doc.filename,
                status=JobStatus.RETRYING,
                current_step=JobStep.KG_INDEXING,
                user_id="phase13_recovery",
                completed_steps=[JobStep.EXTRACTION, JobStep.CHUNKING, JobStep.EMBEDDING],
                total_pages=doc.total_pages,
                chunks_created=doc.total_chunks,
                embeddings_created=doc.total_chunks,
            )
            await job.insert()
        else:
            job = existing_job
            job.status = JobStatus.RETRYING
            job.current_step = JobStep.KG_INDEXING
            await job.save()

        print(f"  Processing job: {job.id}")

        # Update doc status to indexing_kg (it already is, but be explicit)
        doc.status = DocumentStatus.INDEXING_KG
        from app.db.repositories.document_repo import DocumentRepository
        repo = DocumentRepository()
        await repo.update(doc)

        # Delete any stale KG entities first (idempotency)
        print("  Deleting existing KG entities for idempotency...")
        await kg_builder.delete_document_entities(LEDG_DOC_ID)

        # Run KG extraction — this calls LLM with retry/backoff
        print(f"  Running KG extraction on {len(doc.pages)} pages (max 15)...")
        total_entities, total_rels = await kg_builder.build_from_document(
            document_id=LEDG_DOC_ID,
            filename=doc.filename,
            pages=doc.pages,
        )

        print(f"  KG result: {total_entities} entities, {total_rels} relationships")

        # Update document with KG counts and mark completed
        doc.mark_kg_indexed(total_entities, total_rels)
        doc.mark_completed(total_chunks=doc.total_chunks)
        await repo.update(doc)

        # Update job
        job.kg_nodes_created = total_entities
        job.kg_relations_created = total_rels
        job.status = JobStatus.COMPLETED
        job.current_step = JobStep.COMPLETED
        if JobStep.KG_INDEXING not in job.completed_steps:
            job.completed_steps.append(JobStep.KG_INDEXING)
        if JobStep.COMPLETED not in job.completed_steps:
            job.completed_steps.append(JobStep.COMPLETED)
        job.completed_at = datetime.datetime.now(datetime.timezone.utc)
        job.elapsed_seconds = time.time() - start
        await job.save()

        result["success"] = True
        result["kg_entities"] = total_entities
        result["kg_relationships"] = total_rels

    except Exception as exc:
        result["error"] = str(exc)
        print(f"  ERROR: {exc}")
        traceback.print_exc()

    result["duration_seconds"] = round(time.time() - start, 2)
    return result


# ---------------------------------------------------------------------------
# Stage 2: Process acquired_documents
# ---------------------------------------------------------------------------
async def process_acquired_document(
    acq_doc,
    settings,
    indexer,
    kg_builder,
) -> dict:
    """
    Full pipeline for one acquired document:
    download -> validate -> extract -> chunk -> embed -> KG -> mark completed
    """
    from app.models.document import Document, DocumentStatus, DocumentCategory, DocumentType, ExtractedPage
    from app.models.acquisition import AcquiredDocument, AcquisitionStatus
    from app.models.processing_job import ProcessingJob, JobStatus, JobStep
    from app.db.repositories.document_repo import DocumentRepository
    from app.utils.pdf_parser import extract_text_from_pdf
    from app.utils.text_splitter import chunk_text, build_page_boundaries

    doc_id_str = str(acq_doc.id)
    title_safe = (acq_doc.title or "Unknown")[:80].encode("ascii", "replace").decode("ascii")
    pdf_url = acq_doc.pdf_url or ""

    result = {
        "acquired_id": doc_id_str,
        "title": title_safe,
        "pdf_url": pdf_url[:120],
        "document_id": None,
        "filename": None,
        "pages": 0,
        "chunks": 0,
        "kg_entities": 0,
        "kg_relationships": 0,
        "status": "not_started",
        "failure_stage": None,
        "error": "",
        "duration_seconds": 0.0,
        "retry_count": 0,
    }

    start = time.time()
    print(f"\n  Processing: {title_safe[:60]}")

    if not pdf_url:
        result["status"] = "skipped"
        result["failure_stage"] = "download"
        result["error"] = "No pdf_url available"
        print(f"    SKIP: No pdf_url")
        return result

    # --- Download ---
    local_path = f"../uploads/temp_{doc_id_str}.pdf"
    if acq_doc.local_file_path and os.path.exists(acq_doc.local_file_path):
        # Pre-validate existing file
        import fitz
        try:
            pdf = fitz.open(acq_doc.local_file_path)
            pc = pdf.page_count
            text = "".join(pdf[i].get_text() for i in range(min(3, pc)))
            pdf.close()
            if pc >= 1 and len(text.strip()) >= 200:
                local_path = acq_doc.local_file_path
                print(f"    Re-using existing file: {local_path} ({pc} pages)")
                download_ok = True
                download_reason = f"pre-existing ({pc} pages)"
            else:
                download_ok = False
                download_reason = f"pre-existing file invalid (pages={pc}, text_len={len(text.strip())})"
        except Exception as e:
            download_ok = False
            download_reason = f"pre-existing file unreadable: {e}"
    else:
        download_ok = False
        download_reason = "no local file"

    if not download_ok:
        print(f"    Downloading from: {pdf_url[:80]}")
        download_ok, download_reason = await download_pdf(pdf_url, local_path)
        if download_ok:
            acq_doc.local_file_path = local_path
            acq_doc.status = AcquisitionStatus.FULL_REVIEW
            await acq_doc.save()

    if not download_ok:
        result["status"] = "failed"
        result["failure_stage"] = "download"
        result["error"] = download_reason
        print(f"    DOWNLOAD FAILED: {download_reason}")
        result["duration_seconds"] = round(time.time() - start, 2)
        return result

    print(f"    Download: {download_reason}")

    # --- Create Document record ---
    safe_filename = f"acq_{doc_id_str}_{(acq_doc.title or 'paper')[:40].encode('ascii','replace').decode('ascii').replace(' ','_')}.pdf"
    repo = DocumentRepository()

    # Check for existing doc record for this acquired doc
    existing_doc = await Document.find_one({"original_filename": safe_filename})
    if existing_doc and existing_doc.status == DocumentStatus.COMPLETED:
        result["status"] = "already_completed"
        result["document_id"] = str(existing_doc.id)
        result["pages"] = existing_doc.total_pages
        result["chunks"] = existing_doc.total_chunks
        result["kg_entities"] = existing_doc.total_kg_entities
        result["kg_relationships"] = existing_doc.total_kg_relationships
        result["duration_seconds"] = round(time.time() - start, 2)
        print(f"    Already completed (doc_id={result['document_id']})")
        return result

    # Compute SHA256
    with open(local_path, "rb") as f_bin:
        sha256 = hashlib.sha256(f_bin.read()).hexdigest()

    file_size = os.path.getsize(local_path)

    if existing_doc is None:
        import shutil
        upload_dest = f"../uploads/{safe_filename}"
        shutil.copy2(local_path, upload_dest)

        document = Document(
            filename=safe_filename,
            file_path=upload_dest,
            file_size_bytes=file_size,
            content_type="application/pdf",
            document_type=DocumentType.RESEARCH_PAPER,
            status=DocumentStatus.UPLOADED,
            category=DocumentCategory.RESEARCH,
            sha256_hash=sha256,
            version=1,
            original_filename=safe_filename,
            indexed_by="phase13_expansion",
        )
        await repo.create(document)
    else:
        document = existing_doc
        import shutil
        upload_dest = document.file_path
        if not os.path.exists(upload_dest):
            shutil.copy2(local_path, upload_dest)

    doc_id = str(document.id)
    result["document_id"] = doc_id
    result["filename"] = safe_filename

    # --- ProcessingJob ---
    job = ProcessingJob(
        document_id=doc_id,
        filename=safe_filename,
        status=JobStatus.RUNNING,
        current_step=JobStep.EXTRACTION,
        user_id="phase13_expansion",
        started_at=datetime.datetime.now(datetime.timezone.utc),
    )
    await job.insert()

    try:
        # --- EXTRACTION ---
        document.mark_extracting()
        await repo.update(document)

        from app.utils.pdf_parser import extract_text_from_pdf
        extraction_result = extract_text_from_pdf(document.file_path)

        extracted_pages = [
            ExtractedPage(
                page_number=p.page_number,
                text=p.text,
                sections=p.sections,
                char_count=p.char_count,
            )
            for p in extraction_result.pages
        ]

        if not extracted_pages or len(extraction_result.full_text.strip()) < 100:
            raise ValueError(f"Extraction produced insufficient text ({len(extraction_result.full_text.strip())} chars)")

        document.mark_extracted(pages=extracted_pages, full_text=extraction_result.full_text)
        document.metadata = extraction_result.metadata
        document.auto_metadata = {
            "title": acq_doc.title or extraction_result.metadata.get("title", ""),
            "author": ", ".join(acq_doc.authors[:3]) if acq_doc.authors else "",
            "year": acq_doc.year or "",
            "pages": extraction_result.total_pages,
        }
        await repo.update(document)

        result["pages"] = extraction_result.total_pages
        job.completed_steps.append(JobStep.EXTRACTION)
        job.pages_extracted = extraction_result.total_pages
        job.total_pages = extraction_result.total_pages
        job.current_step = JobStep.CHUNKING
        await job.save()
        print(f"    Extracted: {extraction_result.total_pages} pages, {len(extraction_result.full_text)} chars")

        # --- CHUNKING + EMBEDDING ---
        document.status = DocumentStatus.CHUNKING
        await repo.update(document)

        page_boundaries = build_page_boundaries([
            {"page_number": p.page_number, "text": p.text, "sections": p.sections}
            for p in extracted_pages
        ])

        chunks = chunk_text(
            text=extraction_result.full_text,
            document_id=doc_id,
            document_name=safe_filename,
            chunk_size=settings.RAG_CHUNK_SIZE,
            chunk_overlap=settings.RAG_CHUNK_OVERLAP,
            page_boundaries=page_boundaries,
        )
        for chunk in chunks:
            chunk.metadata.update({"is_global": True, "workspace_id": None, "category": "RESEARCH"})

        if not chunks:
            raise ValueError("No chunks generated from extracted text")

        job.completed_steps.append(JobStep.CHUNKING)
        job.chunks_created = len(chunks)
        job.current_step = JobStep.EMBEDDING
        await job.save()

        document.status = DocumentStatus.EMBEDDING
        await repo.update(document)

        # Delete existing chunks first (idempotency)
        await indexer.delete_document_chunks(doc_id)

        indexed_count = await indexer.index_chunks(chunks)
        document.total_chunks = indexed_count
        await repo.update(document)

        result["chunks"] = indexed_count
        job.completed_steps.append(JobStep.EMBEDDING)
        job.embeddings_created = indexed_count
        job.current_step = JobStep.KG_INDEXING
        await job.save()
        print(f"    Embedded: {indexed_count} chunks")

        # --- KG INDEXING ---
        document.status = DocumentStatus.INDEXING_KG
        await repo.update(document)

        await kg_builder.delete_document_entities(doc_id)
        total_entities, total_rels = await kg_builder.build_from_document(
            document_id=doc_id,
            filename=safe_filename,
            pages=extracted_pages,
        )

        document.mark_kg_indexed(total_entities, total_rels)
        result["kg_entities"] = total_entities
        result["kg_relationships"] = total_rels
        job.kg_nodes_created = total_entities
        job.kg_relations_created = total_rels
        job.completed_steps.append(JobStep.KG_INDEXING)
        print(f"    KG: {total_entities} entities, {total_rels} relationships")

        # --- COMPLETED ---
        document.mark_completed(total_chunks=indexed_count)
        await repo.update(document)

        job.status = JobStatus.COMPLETED
        job.current_step = JobStep.COMPLETED
        job.completed_steps.append(JobStep.COMPLETED)
        job.completed_at = datetime.datetime.now(datetime.timezone.utc)
        job.elapsed_seconds = time.time() - start
        await job.save()

        # Mark acquired document as INDEXED
        acq_doc.status = AcquisitionStatus.INDEXED
        await acq_doc.save()

        result["status"] = "completed"
        print(f"    COMPLETED successfully")

    except Exception as exc:
        err_msg = str(exc)
        tb = traceback.format_exc()
        print(f"    FAILED at {job.current_step}: {err_msg[:200]}")

        result["status"] = "failed"
        result["failure_stage"] = str(job.current_step)
        result["error"] = err_msg[:500]

        job.status = JobStatus.FAILED
        job.failed_step = str(job.current_step)
        job.error_message = err_msg[:500]
        job.elapsed_seconds = time.time() - start
        await job.save()

        document.mark_failed(err_msg[:500])
        await repo.update(document)

    result["duration_seconds"] = round(time.time() - start, 2)
    return result


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------
async def main():
    print("=" * 70)
    print("PHASE 13 — CORPUS EXPANSION")
    print("=" * 70)
    print(f"Started: {datetime.datetime.now().isoformat()}")

    # --- Initialize all services ---
    print("\n[INIT] Initializing services...")
    settings, indexer, kg_builder = await init_services()
    print(f"  Settings loaded: MongoDB={settings.MONGODB_DATABASE}, ChromaDB={settings.CHROMADB_COLLECTION}")

    all_results = []
    start_total = time.time()

    # -------------------------------------------------------------------------
    # Stage 1: LEDG Recovery
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("STAGE 1: LEDG KG Recovery")
    print("=" * 70)

    ledg_result = await recover_ledg_kg(settings, kg_builder)
    all_results.append({
        "type": "ledg_recovery",
        **ledg_result,
    })

    print(f"  LEDG result: success={ledg_result['success']}, "
          f"entities={ledg_result['kg_entities']}, rels={ledg_result['kg_relationships']}")
    if not ledg_result["success"]:
        print(f"  LEDG error: {ledg_result['error']}")

    # -------------------------------------------------------------------------
    # Stage 2: Acquired Documents
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("STAGE 2: Acquired Document Processing")
    print("=" * 70)

    from app.models.acquisition import AcquiredDocument, AcquisitionStatus

    # Load all acquired docs, ordered by priority
    # Priority 1: Concrete/carbonation series, self-healing, alkali-activated
    # Priority 2: Seismic retrofitting
    all_acq = await AcquiredDocument.find_all().to_list()

    # Skip already properly indexed ones that already have real document records
    from app.models.document import Document, DocumentStatus
    already_indexed = await Document.find({"status": "completed"}).to_list()
    already_indexed_sha = {d.sha256_hash for d in already_indexed}

    print(f"\nTotal acquired_documents: {len(all_acq)}")
    print(f"Already completed documents: {len(already_indexed)}")

    acq_results = []
    for i, acq_doc in enumerate(all_acq):
        doc_type_label = (
            "Concrete/Materials" if i < 10 else "Seismic/Structural"
        )
        print(f"\n[{i+1}/{len(all_acq)}] {doc_type_label}")

        # Small delay between documents to be gentle on Groq
        if i > 0:
            await asyncio.sleep(2)

        res = await process_acquired_document(acq_doc, settings, indexer, kg_builder)
        acq_results.append(res)
        all_results.append({"type": "acquired_document", **res})

        # Brief status
        status_emoji = "OK" if res["status"] == "completed" else "FAIL" if res["status"] == "failed" else res["status"].upper()
        print(f"  [{status_emoji}] {res['title'][:50]} -> {res['status']}")
        if res.get("error"):
            print(f"         Error: {res['error'][:100]}")

    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------
    total_duration = round(time.time() - start_total, 2)

    completed_acq = [r for r in acq_results if r["status"] == "completed"]
    failed_acq = [r for r in acq_results if r["status"] == "failed"]
    skipped_acq = [r for r in acq_results if r["status"] in ("skipped", "already_completed")]

    summary = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "total_duration_seconds": total_duration,
        "ledg_recovery": {
            "success": ledg_result["success"],
            "kg_entities": ledg_result["kg_entities"],
            "kg_relationships": ledg_result["kg_relationships"],
            "error": ledg_result["error"],
            "duration_seconds": ledg_result["duration_seconds"],
        },
        "acquired_documents": {
            "total": len(all_acq),
            "completed": len(completed_acq),
            "failed": len(failed_acq),
            "skipped_or_already_done": len(skipped_acq),
            "total_chunks": sum(r["chunks"] for r in completed_acq),
            "total_kg_entities": sum(r["kg_entities"] for r in completed_acq),
            "total_kg_relationships": sum(r["kg_relationships"] for r in completed_acq),
        },
        "results": all_results,
    }

    # --- Save JSON ---
    json_path = OUTPUT_DIR / "corpus_expansion_report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"\nJSON saved: {json_path}")

    # --- Save Markdown ---
    md_lines = [
        "# Phase 13 — Corpus Expansion Report",
        "",
        f"**Generated:** {summary['generated_at']}",
        f"**Total Duration:** {total_duration:.1f} seconds",
        "",
        "## LEDG Recovery",
        f"- Success: {ledg_result['success']}",
        f"- KG Entities: {ledg_result['kg_entities']}",
        f"- KG Relationships: {ledg_result['kg_relationships']}",
        f"- Duration: {ledg_result['duration_seconds']}s",
    ]
    if ledg_result["error"]:
        md_lines.append(f"- Error: `{ledg_result['error'][:200]}`")

    md_lines += [
        "",
        "## Acquired Document Processing",
        f"- Total acquired documents: {len(all_acq)}",
        f"- Completed: {len(completed_acq)}",
        f"- Failed: {len(failed_acq)}",
        f"- Skipped/Already Done: {len(skipped_acq)}",
        f"- Total new chunks: {summary['acquired_documents']['total_chunks']}",
        f"- Total new KG entities: {summary['acquired_documents']['total_kg_entities']}",
        f"- Total new KG relationships: {summary['acquired_documents']['total_kg_relationships']}",
        "",
        "## Per-Document Results",
        "",
        "| # | Title | Status | Pages | Chunks | KG Entities | Error |",
        "|---|-------|--------|-------|--------|-------------|-------|",
    ]
    for i, r in enumerate(acq_results, 1):
        err = r.get("error", "")[:50] if r.get("error") else ""
        md_lines.append(
            f"| {i} | {r['title'][:40]} | {r['status']} "
            f"| {r['pages']} | {r['chunks']} | {r['kg_entities']} | {err} |"
        )

    md_lines += [
        "",
        "## Notes",
        "- All values are live runtime measurements",
        "- No fabricated data",
        "- Documents were processed through the production pipeline only",
    ]

    md_path = OUTPUT_DIR / "corpus_expansion_report.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))
    print(f"Markdown saved: {md_path}")

    # --- Console summary ---
    print("\n" + "=" * 70)
    print("CORPUS EXPANSION COMPLETE")
    print("=" * 70)
    print(f"LEDG recovery:          {'SUCCESS' if ledg_result['success'] else 'FAILED'}")
    print(f"Acquired docs completed: {len(completed_acq)} / {len(all_acq)}")
    print(f"Acquired docs failed:    {len(failed_acq)}")
    print(f"Total duration:          {total_duration:.1f}s")
    print("=" * 70)

    return summary


if __name__ == "__main__":
    asyncio.run(main())
