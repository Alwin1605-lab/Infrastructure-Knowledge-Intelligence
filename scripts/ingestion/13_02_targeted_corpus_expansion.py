"""
Phase 13 — Targeted Multi-Domain Corpus Expansion Script
=========================================================
Expands the genuine research corpus to ~20-25 documents prioritizing domain diversity:
  1. Geotechnical / Foundation Engineering (2-3 OA PDFs)
  2. Fire Safety / Building Fire Engineering (2-3 OA PDFs)
  3. Inspection / Maintenance (2-3 OA PDFs)
  4. Repair / Rehabilitation (1-2 OA PDFs)
  5. Environmental / Sustainability (1-2 OA PDFs)
  6. Additional structural/seismic papers if needed

No Fabrication Policy:
  - Validates real Open Access PDFs via ArXiv / direct OA sources.
  - A document is only counted when PDF exists, extraction succeeds, ChromaDB chunks exist,
    embeddings exist, and Neo4j KG processing succeeds.
  - Generates detailed acquisition logs & final corpus diversity report.
"""

import asyncio
import sys
import os
import json
import time
import datetime
import hashlib
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import ssl
import traceback
from pathlib import Path

# Bootstrap backend paths
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))
os.chdir(BACKEND_DIR)

OUTPUT_DIR = Path("../experiments/v3")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/pdf,*/*"
}

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

# ---------------------------------------------------------------------------
# Service Initialization
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
    await init_db(settings)
    await init_vectorstore(settings)
    await init_kg(settings)

    embedding_svc = HuggingFaceEmbeddingService(settings)
    llm_provider = create_llm_provider(settings)
    indexer = ChromaIndexer(embedding_service=embedding_svc)
    kg_builder = KGBuilder(llm_provider=llm_provider)

    return settings, indexer, kg_builder

# ---------------------------------------------------------------------------
# Candidate Acquisition Helpers
# ---------------------------------------------------------------------------
def search_arxiv_candidates(query, category_name, max_results=6):
    encoded = urllib.parse.quote(query)
    url = f"https://export.arxiv.org/api/query?search_query={encoded}&max_results={max_results}&sortBy=relevance"
    req = urllib.request.Request(url, headers=HEADERS)
    candidates = []
    try:
        with urllib.request.urlopen(req, timeout=20, context=SSL_CTX) as resp:
            data = resp.read().decode('utf-8')
            root = ET.fromstring(data)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            for entry in root.findall('atom:entry', ns):
                title = entry.find('atom:title', ns).text.strip().replace('\n', ' ')
                summary = entry.find('atom:summary', ns).text.strip().replace('\n', ' ')
                arxiv_id = entry.find('atom:id', ns).text.strip().split('/abs/')[-1]
                pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
                candidates.append({
                    'title': title,
                    'summary': summary,
                    'pdf_url': pdf_url,
                    'source': 'arXiv',
                    'oa_status': 'Open Access (arXiv)',
                    'domain_category': category_name,
                    'arxiv_id': arxiv_id
                })
    except Exception as e:
        print(f"arXiv error ({query}): {e}")
    return candidates

# ---------------------------------------------------------------------------
# Robust PDF Downloader & Validator
# ---------------------------------------------------------------------------
async def download_and_validate_pdf(pdf_url: str, target_path: str) -> tuple[bool, str, int, int]:
    import httpx
    import fitz

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=60.0, headers=HEADERS) as client:
            resp = await client.get(pdf_url)
            if resp.status_code != 200:
                return False, f"HTTP {resp.status_code}", 0, 0
            content = resp.content
            if len(content) < 5000:
                return False, f"File too small ({len(content)} bytes)", len(content), 0

            with open(target_path, "wb") as f:
                f.write(content)

            try:
                doc = fitz.open(target_path)
                page_count = doc.page_count
                if page_count < 1:
                    doc.close()
                    if os.path.exists(target_path): os.remove(target_path)
                    return False, "PDF has 0 pages", len(content), 0

                text = ""
                for p_i in range(min(3, page_count)):
                    text += doc[p_i].get_text()
                doc.close()

                if len(text.strip()) < 200:
                    if os.path.exists(target_path): os.remove(target_path)
                    return False, f"Insufficient text ({len(text.strip())} chars)", len(content), page_count

                return True, f"OK ({page_count} pages)", len(content), page_count
            except Exception as pdf_err:
                if os.path.exists(target_path): os.remove(target_path)
                return False, f"PDF validation failed: {pdf_err}", len(content), 0

    except Exception as exc:
        if os.path.exists(target_path): os.remove(target_path)
        return False, f"Download error: {exc}", 0, 0

# ---------------------------------------------------------------------------
# Production Ingestion Execution
# ---------------------------------------------------------------------------
async def process_candidate_paper(candidate: dict, settings, indexer, kg_builder) -> dict:
    from app.models.document import Document, DocumentStatus, DocumentCategory, DocumentType, ExtractedPage
    from app.models.acquisition import AcquiredDocument, AcquisitionStatus
    from app.models.processing_job import ProcessingJob, JobStatus, JobStep
    from app.utils.pdf_parser import extract_text_from_pdf
    from app.utils.text_splitter import chunk_text, build_page_boundaries

    title = candidate['title']
    pdf_url = candidate['pdf_url']
    domain_cat = candidate['domain_category']
    source = candidate['source']
    oa_status = candidate['oa_status']

    record_log = {
        "title": title,
        "source": source,
        "url": pdf_url,
        "oa_status": oa_status,
        "domain_category": domain_cat,
        "download_status": "PENDING",
        "processing_status": "PENDING",
        "failure_reason": None,
        "pages": 0,
        "chunks": 0,
        "kg_entities": 0,
        "kg_relationships": 0,
        "document_id": None,
    }

    print(f"\nProcessing Candidate: [{domain_cat}] {title[:65]}...")

    # Create AcquiredDocument record in MongoDB
    acq_doc = await AcquiredDocument.find_one({"source_url": pdf_url})
    if acq_doc is None:
        acq_doc = AcquiredDocument(
            source_url=pdf_url,
            pdf_url=pdf_url,
            title=title,
            status=AcquisitionStatus.METADATA_REVIEW
        )
        await acq_doc.insert()

    # Target path
    safe_title = "".join(c if c.isalnum() else "_" for c in title[:30])
    filename = f"acq_{domain_cat[:4].upper()}_{candidate.get('arxiv_id','doc')}_{safe_title}.pdf"
    target_path = f"uploads/{filename}"

    # Step 1: Download & Validate
    valid, reason, size, pages = await download_and_validate_pdf(pdf_url, target_path)
    if not valid:
        record_log["download_status"] = "FAILED"
        record_log["processing_status"] = "FAILED"
        record_log["failure_reason"] = f"Download/Validate failed: {reason}"
        acq_doc.status = AcquisitionStatus.REJECTED
        await acq_doc.save()
        print(f"  FAILED Download: {reason}")
        return record_log

    record_log["download_status"] = "SUCCESS"
    record_log["pages"] = pages
    print(f"  Downloaded & Validated: {pages} pages ({size/1024:.1f} KB)")

    # Step 2: Check for existing MongoDB Document
    with open(target_path, "rb") as f:
        sha256 = hashlib.sha256(f.read()).hexdigest()

    existing_doc = await Document.find_one({"sha256_hash": sha256})
    if existing_doc and existing_doc.status == DocumentStatus.COMPLETED:
        record_log["processing_status"] = "COMPLETED"
        record_log["document_id"] = str(existing_doc.id)
        record_log["chunks"] = existing_doc.total_chunks
        record_log["kg_entities"] = existing_doc.total_kg_entities
        record_log["kg_relationships"] = existing_doc.total_kg_relationships
        print(f"  Already completed in DB: doc_id={existing_doc.id}")
        return record_log

    if existing_doc is None:
        doc_record = Document(
            filename=filename,
            file_path=target_path,
            file_size_bytes=size,
            content_type="application/pdf",
            document_type=DocumentType.RESEARCH_PAPER,
            status=DocumentStatus.UPLOADED,
            category=DocumentCategory.RESEARCH,
            sha256_hash=sha256,
            version=1,
            original_filename=filename,
            indexed_by="phase13_expansion",
        )
        await doc_record.insert()
    else:
        doc_record = existing_doc

    doc_id = str(doc_record.id)
    record_log["document_id"] = doc_id

    # Step 3: Production Processing Job
    job = ProcessingJob(
        document_id=doc_id,
        filename=filename,
        status=JobStatus.RUNNING,
        current_step=JobStep.EXTRACTION,
        user_id="phase13_expansion",
        started_at=datetime.datetime.now(datetime.timezone.utc),
    )
    await job.insert()

    try:
        # A. Extraction
        doc_record.mark_extracting()
        await doc_record.save()

        extraction_result = extract_text_from_pdf(doc_record.file_path)
        extracted_pages = [
            ExtractedPage(
                page_number=p.page_number,
                text=p.text,
                sections=p.sections,
                char_count=p.char_count,
            ) for p in extraction_result.pages
        ]

        if not extracted_pages or len(extraction_result.full_text.strip()) < 100:
            raise ValueError("Insufficient text extracted")

        doc_record.mark_extracted(pages=extracted_pages, full_text=extraction_result.full_text)
        doc_record.auto_metadata = {
            "title": title,
            "domain_category": domain_cat,
            "source": source,
            "pages": extraction_result.total_pages
        }
        await doc_record.save()

        # B. Chunking & Embedding
        doc_record.status = DocumentStatus.CHUNKING
        await doc_record.save()

        page_boundaries = build_page_boundaries([
            {"page_number": p.page_number, "text": p.text, "sections": p.sections}
            for p in extracted_pages
        ])

        chunks = chunk_text(
            text=extraction_result.full_text,
            document_id=doc_id,
            document_name=filename,
            chunk_size=settings.RAG_CHUNK_SIZE,
            chunk_overlap=settings.RAG_CHUNK_OVERLAP,
            page_boundaries=page_boundaries,
        )

        for chunk in chunks:
            chunk.metadata.update({
                "is_global": True,
                "workspace_id": None,
                "category": domain_cat
            })

        doc_record.status = DocumentStatus.EMBEDDING
        await doc_record.save()

        await indexer.delete_document_chunks(doc_id)
        indexed_count = await indexer.index_chunks(chunks)
        doc_record.total_chunks = indexed_count
        await doc_record.save()
        record_log["chunks"] = indexed_count
        print(f"  Extracted {len(extracted_pages)} pages, Embedded {indexed_count} chunks")

        # C. Knowledge Graph Indexing
        doc_record.status = DocumentStatus.INDEXING_KG
        await doc_record.save()

        await kg_builder.delete_document_entities(doc_id)
        kg_entities, kg_rels = await kg_builder.build_from_document(
            document_id=doc_id,
            filename=filename,
            pages=extracted_pages,
        )

        doc_record.mark_kg_indexed(kg_entities, kg_rels)
        record_log["kg_entities"] = kg_entities
        record_log["kg_relationships"] = kg_rels
        print(f"  KG Indexing: {kg_entities} entities, {kg_rels} relationships")

        # D. Mark Completed
        doc_record.mark_completed(total_chunks=indexed_count)
        await doc_record.save()

        job.status = JobStatus.COMPLETED
        job.current_step = JobStep.COMPLETED
        job.completed_at = datetime.datetime.now(datetime.timezone.utc)
        await job.save()

        acq_doc.status = AcquisitionStatus.INDEXED
        acq_doc.local_file_path = target_path
        await acq_doc.save()

        record_log["processing_status"] = "COMPLETED"
        print(f"  COMPLETED SUCCESSFULLY: doc_id={doc_id}")

    except Exception as exc:
        err_msg = str(exc)
        doc_record.mark_failed(error_message=err_msg)
        await doc_record.save()
        job.mark_failed(error_message=err_msg)
        await job.save()
        acq_doc.status = AcquisitionStatus.REJECTED
        await acq_doc.save()

        record_log["processing_status"] = "FAILED"
        record_log["failure_reason"] = f"Pipeline error: {err_msg}"
        print(f"  PIPELINE FAILED: {err_msg}")

    return record_log

# ---------------------------------------------------------------------------
# Main Expansion Loop
# ---------------------------------------------------------------------------
async def main():
    print("======================================================================")
    print("PHASE 13 — TARGETED MULTI-DOMAIN CORPUS EXPANSION")
    print("======================================================================")

    settings, indexer, kg_builder = await init_services()

    # Target priorities & queries
    target_plan = [
        ("Geotechnical / Foundation Engineering", 3, [
            'all:"geotechnical engineering" AND (all:soil OR all:foundation OR all:slope)',
            'all:"shallow foundation" AND all:"bearing capacity"',
            'all:"slope stability analysis" AND all:"soil mechanics"'
        ]),
        ("Fire Safety / Building Fire Engineering", 3, [
            'all:"building fire safety" OR all:"structural fire engineering"',
            'all:"fire resistance" AND all:"reinforced concrete beam"',
            'all:"building fire risk assessment"'
        ]),
        ("Inspection / Maintenance", 3, [
            'all:"structural health monitoring" AND (all:bridge OR all:building)',
            'all:"non destructive testing" AND all:"concrete inspection"',
            'all:"vibration based structural health monitoring"'
        ]),
        ("Repair / Rehabilitation", 2, [
            'all:"structural retrofitting" AND all:"concrete repair"',
            'all:"structural rehabilitation" AND all:"concrete column"'
        ]),
        ("Environmental / Sustainability", 2, [
            'all:"life cycle assessment" AND all:"building construction"',
            'all:"embodied carbon" AND all:"building materials"'
        ])
    ]

    acquisition_logs = []

    # Check current completed count first
    from app.models.document import Document, DocumentStatus
    completed_docs = await Document.find({"status": DocumentStatus.COMPLETED.value}).to_list()
    current_count = len(completed_docs)
    print(f"Current verified baseline completed docs: {current_count}")

    TARGET_MAX = 22  # Goal: ~20-25 genuine docs

    for domain_cat, target_num, queries in target_plan:
        if current_count >= TARGET_MAX:
            print(f"\nTarget count of {TARGET_MAX} reached. Stopping expansion.")
            break

        print(f"\n----------------------------------------------------------------------")
        print(f"TARGETING DOMAIN: {domain_cat} (Target: {target_num} docs)")
        print(f"----------------------------------------------------------------------")

        domain_added = 0
        for q in queries:
            if domain_added >= target_num or current_count >= TARGET_MAX:
                break

            print(f"Searching arXiv query: '{q}' ...")
            candidates = search_arxiv_candidates(q, domain_cat, max_results=5)

            for cand in candidates:
                if domain_added >= target_num or current_count >= TARGET_MAX:
                    break

                # Process candidate paper
                log_entry = await process_candidate_paper(cand, settings, indexer, kg_builder)
                acquisition_logs.append(log_entry)

                if log_entry["processing_status"] == "COMPLETED":
                    domain_added += 1
                    current_count += 1
                    print(f"  --> Progress: {current_count} total completed docs (+{domain_added} for {domain_cat})")

    # Save Acquisition Log JSON
    log_file = OUTPUT_DIR / "acquisition_log.json"
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(acquisition_logs, f, indent=2)
    print(f"\nAcquisition log saved to: {log_file}")

    print("\nExecuting discovery verification script...")
    os.system("python ../scripts/13_01_discover_corpus.py")

if __name__ == "__main__":
    asyncio.run(main())
