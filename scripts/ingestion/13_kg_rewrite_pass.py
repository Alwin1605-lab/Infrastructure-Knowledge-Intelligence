#!/usr/bin/env python3
"""
Phase 13 — Full KG Re-write Pass
==================================
The corpus expansion run successfully extracted KG entities via LLM but
failed to write them to Neo4j (await bug). MongoDB has correct entity counts.

This script re-runs KG extraction + Neo4j write for ALL completed documents
that currently have 0 Neo4j nodes written (identified by cross-checking
document_id against Neo4j).

It processes from MongoDB pages (already stored), never re-embeds, never
re-downloads. Each document is processed in full pipeline order:
  delete_document_entities -> build_from_document (LLM -> Neo4j write)
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
    await init_kg(settings)  # properly awaited
    llm_provider = create_llm_provider(settings)
    kg_builder = KGBuilder(llm_provider=llm_provider)
    return settings, kg_builder


async def get_neo4j_doc_ids(driver) -> set:
    """Return set of document_ids that already have domain entity nodes in Neo4j."""
    doc_ids = set()
    async with driver.session() as session:
        result = await session.run(
            "MATCH (n) WHERE n.document_id IS NOT NULL AND NOT n:Document "
            "RETURN DISTINCT n.document_id AS doc_id"
        )
        async for record in result:
            doc_ids.add(record["doc_id"])
    return doc_ids


async def main():
    print("=" * 70)
    print("PHASE 13 — FULL KG RE-WRITE PASS")
    print("=" * 70)
    print(f"Started: {datetime.datetime.now().isoformat()}")

    settings, kg_builder = await init_services()

    from app.models.document import Document, DocumentStatus
    from app.db.repositories.document_repo import DocumentRepository
    from app.knowledge_graph.connection import get_neo4j_driver

    repo = DocumentRepository()
    driver = get_neo4j_driver()

    # Get all document IDs already in Neo4j
    neo4j_doc_ids = await get_neo4j_doc_ids(driver)
    print(f"Document IDs currently in Neo4j: {len(neo4j_doc_ids)}")
    for did in sorted(neo4j_doc_ids):
        print(f"  {did}")

    # Find all completed documents with pages available
    all_docs = await Document.find({"status": "completed"}).to_list()
    print(f"\nAll completed documents: {len(all_docs)}")

    # Target: completed docs with pages that are NOT yet in Neo4j
    targets = [
        d for d in all_docs
        if str(d.id) not in neo4j_doc_ids and d.pages
    ]
    print(f"Targets (completed, has pages, not in Neo4j): {len(targets)}")

    if not targets:
        print("All completed documents already have Neo4j data. Nothing to do.")
        # Still run discovery
    else:
        for i, doc in enumerate(targets):
            doc_id = str(doc.id)
            print(f"\n  [{i+1}/{len(targets)}] {doc.filename[:60]}")
            print(f"    pages={len(doc.pages)}, chunks={doc.total_chunks}, "
                  f"mongo_entities={doc.total_kg_entities}")

            start = time.time()
            try:
                await kg_builder.delete_document_entities(doc_id)
                total_entities, total_rels = await kg_builder.build_from_document(
                    document_id=doc_id,
                    filename=doc.filename,
                    pages=doc.pages,
                )
                print(f"    KG written: {total_entities} entities, {total_rels} rels "
                      f"({time.time()-start:.1f}s)")

                doc.mark_kg_indexed(total_entities, total_rels)
                await repo.update(doc)

            except Exception as exc:
                print(f"    FAILED: {exc}")
                traceback.print_exc()

            await asyncio.sleep(2)

    # Verify final Neo4j state
    print("\n" + "=" * 70)
    print("FINAL NEO4J STATE")
    print("=" * 70)
    neo4j_doc_ids_after = await get_neo4j_doc_ids(driver)
    async with driver.session() as session:
        r = await session.run("MATCH (n) RETURN labels(n)[0] AS label, count(n) AS cnt ORDER BY label")
        print("Node counts by label:")
        async for record in r:
            print(f"  {record['label']}: {record['cnt']}")

        r2 = await session.run("MATCH ()-[r]->() RETURN type(r) AS rel_type, count(r) AS cnt ORDER BY rel_type")
        print("Relationship counts by type:")
        async for record in r2:
            print(f"  {record['rel_type']}: {record['cnt']}")

        r3 = await session.run("MATCH (n) WHERE n.document_id IS NOT NULL RETURN DISTINCT n.document_id AS did, count(n) AS cnt ORDER BY did")
        print("Nodes per document_id:")
        async for record in r3:
            print(f"  {record['did']}: {record['cnt']} nodes")

    # Save report
    report = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "neo4j_doc_ids_before": sorted(list(neo4j_doc_ids)),
        "neo4j_doc_ids_after": sorted(list(neo4j_doc_ids_after)),
        "targets_processed": len(targets),
    }
    report_path = OUTPUT_DIR / "kg_rewrite_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved: {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
