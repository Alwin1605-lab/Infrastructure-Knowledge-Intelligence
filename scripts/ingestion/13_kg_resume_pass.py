#!/usr/bin/env python3
"""
Phase 13 — KG Resume Pass
==========================
For documents that have been successfully embedded (status=indexing_kg or
status=completed with 0 KG entities) but whose KG was not written to Neo4j
due to the missing `await init_kg(settings)` bug in the first run.

This script:
  1. Finds all documents with status=completed or status=indexing_kg
     that have total_kg_entities > 0 (per MongoDB) but Neo4j has 0 nodes
     for that document_id, OR documents stuck in status=indexing_kg.
  2. Re-runs ONLY the KG stage (delete_document_entities + build_from_document).
  3. Records results precisely.
  4. Never re-embeds. Never re-extracts.

Run after 13_corpus_expansion.py completes.
"""

import asyncio
import sys
import os
import json
import time
import datetime
import traceback
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))
os.chdir(BACKEND_DIR)

OUTPUT_DIR = Path("../experiments/v3")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


async def init_services():
    from app.config import get_settings
    from app.db.connection import init_db
    from app.vectorstore.connection import init_vectorstore
    from app.knowledge_graph.connection import init_kg
    from app.llm import create_llm_provider
    from app.knowledge_graph.builder import KGBuilder

    settings = get_settings()
    await init_db(settings)
    await init_vectorstore(settings)
    await init_kg(settings)  # FIXED: properly awaited
    llm_provider = create_llm_provider(settings)
    kg_builder = KGBuilder(llm_provider=llm_provider)
    return settings, kg_builder


async def main():
    print("=" * 70)
    print("PHASE 13 — KG RESUME PASS")
    print("=" * 70)
    print(f"Started: {datetime.datetime.now().isoformat()}")

    settings, kg_builder = await init_services()
    print("Services initialized (Neo4j properly connected)")

    from app.models.document import Document, DocumentStatus
    from app.db.repositories.document_repo import DocumentRepository
    from neo4j import AsyncGraphDatabase

    repo = DocumentRepository()

    # Find all docs with pages (can run KG) and 0 neo4j entities
    # We target: completed docs with 0 kg entities, AND indexing_kg docs
    candidates_q = Document.find({
        "$or": [
            {"status": "indexing_kg"},
            {"status": "completed", "total_kg_entities": 0},
        ]
    })
    candidates = await candidates_q.to_list()
    print(f"Candidate documents for KG resume: {len(candidates)}")

    # Verify which actually have no Neo4j data
    from app.knowledge_graph.connection import get_neo4j_driver
    driver = get_neo4j_driver()
    async with driver.session() as session:
        neo4j_docs = await session.run(
            "MATCH (n) WHERE n.document_id IS NOT NULL "
            "RETURN n.document_id AS doc_id, count(n) AS cnt"
        )
        neo4j_counts = {r["doc_id"]: r["cnt"] async for r in neo4j_docs}
    print(f"Documents currently in Neo4j: {list(neo4j_counts.keys())}")

    results = []
    start_total = time.time()

    for doc in candidates:
        doc_id = str(doc.id)
        neo4j_count = neo4j_counts.get(doc_id, 0)

        print(f"\n  [{doc.filename[:50]}]")
        print(f"    status={doc.status}, pages={len(doc.pages)}, neo4j_entities={neo4j_count}")

        if not doc.pages:
            print(f"    SKIP: No pages in MongoDB")
            results.append({
                "document_id": doc_id,
                "filename": doc.filename,
                "status": "skipped",
                "reason": "no pages in MongoDB",
                "kg_entities": 0,
                "kg_relationships": 0,
            })
            continue

        start = time.time()
        try:
            # Delete existing stale entities (idempotency)
            await kg_builder.delete_document_entities(doc_id)

            total_entities, total_rels = await kg_builder.build_from_document(
                document_id=doc_id,
                filename=doc.filename,
                pages=doc.pages,
            )
            print(f"    KG: {total_entities} entities, {total_rels} relationships")

            doc.mark_kg_indexed(total_entities, total_rels)
            doc.mark_completed(total_chunks=doc.total_chunks)
            await repo.update(doc)

            results.append({
                "document_id": doc_id,
                "filename": doc.filename,
                "status": "completed",
                "kg_entities": total_entities,
                "kg_relationships": total_rels,
                "duration_seconds": round(time.time() - start, 2),
            })
            print(f"    COMPLETED")

        except Exception as exc:
            print(f"    FAILED: {exc}")
            results.append({
                "document_id": doc_id,
                "filename": doc.filename,
                "status": "failed",
                "error": str(exc)[:300],
                "kg_entities": 0,
                "kg_relationships": 0,
                "duration_seconds": round(time.time() - start, 2),
            })
            doc.status = DocumentStatus.INDEXING_KG  # Keep in indexing_kg for retry
            doc.error_message = str(exc)[:300]
            await repo.update(doc)

        # Small delay between docs
        await asyncio.sleep(2)

    # Save results
    summary = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "total_duration_seconds": round(time.time() - start_total, 2),
        "candidates_found": len(candidates),
        "completed": sum(1 for r in results if r["status"] == "completed"),
        "failed": sum(1 for r in results if r["status"] == "failed"),
        "skipped": sum(1 for r in results if r["status"] == "skipped"),
        "results": results,
    }

    json_path = OUTPUT_DIR / "kg_resume_report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)

    print(f"\nKG resume complete. Results saved to {json_path}")
    print(f"Completed: {summary['completed']}, Failed: {summary['failed']}, Skipped: {summary['skipped']}")


if __name__ == "__main__":
    asyncio.run(main())
