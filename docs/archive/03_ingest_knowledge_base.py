import argparse
import asyncio
import json
import os
import time
import sys

# Ensure backend modules can be imported
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))

from app.services.document_service import DocumentService
from app.config import get_settings
from app.vectorstore.indexer import ChromaIndexer
from app.knowledge_graph.builder import KGBuilder
from app.llm.groq_provider import GroqProvider

async def main():
    parser = argparse.ArgumentParser(description="Ingest knowledge base documents.")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be processed without processing.")
    parser.add_argument("--limit", type=int, default=0, help="Maximum number of documents to process.")
    parser.add_argument("--resume", action="store_true", help="Resume failed/partial/timeout documents.")
    parser.add_argument("--document", type=str, help="Process a specific document by filename.")
    parser.add_argument("--timeout", type=int, default=14400, help="Global ingestion timeout in seconds (default 4 hours).")
    args = parser.parse_args()

    print(f"Starting ingestion (dry-run: {args.dry_run}, limit: {args.limit}, resume: {args.resume}, timeout: {args.timeout}s)...")
    
    with open("knowledge_base_selection.json", "r", encoding="utf-8") as f:
        selection = json.load(f)

    if args.document:
        selection = [s for s in selection if s["filename"] == args.document]

    if args.resume:
        # Only process docs that are not COMPLETED, or if they have no job.
        # "COMPLETED" job status means fully indexed.
        resume_statuses = ["NOT_FOUND", "FAILED", "TIMEOUT", "RATE_LIMITED", "PARTIAL", "QUEUED"]
        selection = [s for s in selection if s["processing_job_status"] in resume_statuses]
    
    if args.limit > 0:
        selection = selection[:args.limit]

    print(f"Found {len(selection)} documents to process.")

    if args.dry_run:
        for s in selection:
            print(f"Would process: {s['filename']}")
        return

    # Initialize services
    from motor.motor_asyncio import AsyncIOMotorClient
    from beanie import init_beanie
    from app.models.document import Document
    from app.models.workspace_document import WorkspaceDocument
    from app.models.processing_job import ProcessingJob
    from app.models.notification import Notification
    
    settings = get_settings()
    settings.MONGODB_URI = "mongodb://localhost:27017"
    
    mongo_client = AsyncIOMotorClient(settings.MONGODB_URI)
    await init_beanie(
        database=mongo_client[settings.MONGODB_DATABASE],
        document_models=[Document, WorkspaceDocument, ProcessingJob, Notification]
    )
    from app.vectorstore.connection import init_vectorstore
    from app.embedding.huggingface import HuggingFaceEmbeddingService
    await init_vectorstore(settings)
    
    embedding_service = HuggingFaceEmbeddingService(settings)
    chroma_indexer = ChromaIndexer(embedding_service=embedding_service)
    llm_provider = GroqProvider(settings)
    kg_builder = KGBuilder(llm_provider)
    
    doc_service = DocumentService(
        settings=settings,
        chroma_indexer=chroma_indexer,
        kg_builder=kg_builder,
    )
    
    start_time = time.time()
    
    for idx, doc_meta in enumerate(selection):
        elapsed = time.time() - start_time
        if elapsed > args.timeout:
            print(f"Global timeout reached ({args.timeout}s). Stopping ingestion gracefully.")
            break
            
        print(f"[{idx+1}/{len(selection)}] Processing {doc_meta['filename']}...")
        
        # We need a file-like object to pass to upload_and_queue
        # Wait, if it's already in DB and we're resuming, `upload_and_queue` creates a new ProcessingJob.
        # To avoid duplicates, `upload_and_queue` checks sha256. 
        # But wait, `upload_and_queue` doesn't strictly reuse the old job, it makes a new one. 
        # Let's just use `upload_and_queue` and pass the open file.
        # But `upload_and_queue` returns the job, and starts `_process_document_background`.
        # To run synchronously, we can just call `_process_document_background` directly!
        
        try:
            from app.models.document import Document
            # Check if doc exists
            existing_doc = await Document.find_one({"sha256_hash": doc_meta["sha256"]})
            
            if not existing_doc:
                print(f"  Uploading {doc_meta['filename']}...")
                from app.utils.file_handler import validate_content_type
                
                with open(os.path.join(doc_meta["relative_path"]), "rb") as f:
                    # Let's use upload_and_queue but it runs in background
                    # So we'll sleep and poll job status, OR we can just bypass it and do the sync work.
                    # Since we want to respect timeouts, polling is easy.
                    job = await doc_service.upload_and_queue(
                        file=f,
                        filename=doc_meta["filename"],
                        content_type="application/pdf",
                        category=doc_meta["category"]
                    )
                    
                # Poll job until done
                while True:
                    curr_job = await doc_service.get_job_status(str(job.id))
                    if curr_job.status in ["completed", "failed", "timeout", "rate_limited", "partial"]:
                        print(f"  Job finished with status: {curr_job.status}")
                        break
                    await asyncio.sleep(5)
            else:
                from app.models.processing_job import ProcessingJob
                job = await ProcessingJob.find({"document_id": str(existing_doc.id)}).sort("-created_at").first_or_none()
                if not job:
                    job = ProcessingJob(
                        document_id=str(existing_doc.id),
                        filename=existing_doc.filename,
                        user_id="system"
                    )
                    await job.insert()
                
                print(f"  Resuming job {job.id} for {doc_meta['filename']}...")
                await doc_service._process_document_background(
                    job=job,
                    document=existing_doc,
                    is_duplicate=True,
                    owner_id="system"
                )
                print(f"  Job finished with status: {job.status}")

        except Exception as e:
            print(f"  Error triggering process for {doc_meta['filename']}: {e}")

    print("Ingestion script completed.")

if __name__ == "__main__":
    asyncio.run(main())
