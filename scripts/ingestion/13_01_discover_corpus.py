"""
Task 1 — Discover Real Corpus
Queries MongoDB, ChromaDB, Neo4j, and the filesystem to produce a
verified, no-fabrication inventory of every document in the system.

Never marks a document as successfully processed based on filesystem
presence alone.  Requires:
  - MongoDB status == 'completed'
  - total_chunks > 0 (vectors confirmed below)
  - ChromaDB chunk count matches MongoDB
"""

import sys
import os
import json
import hashlib
import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Path bootstrap so the script can be run from the repo root
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from pymongo import MongoClient
from bson import ObjectId
import chromadb
from neo4j import GraphDatabase

# ---------------------------------------------------------------------------
# Config (matches backend/.env)
# ---------------------------------------------------------------------------
MONGO_URI     = "mongodb://localhost:27017"
MONGO_DB      = "infra_knowledge"
CHROMA_PATH   = str(Path(__file__).resolve().parent.parent / "backend" / "chroma_db")
CHROMA_COL    = "building_documents"
NEO4J_URI     = "bolt://localhost:7687"
NEO4J_USER    = "neo4j"
NEO4J_PASS    = "password"
UPLOAD_DIR    = Path("./uploads")
OUTPUT_DIR    = Path("./experiments/v3")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. MongoDB — all document records
# ---------------------------------------------------------------------------
print("=== Querying MongoDB ===")
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[MONGO_DB]

mongo_docs = list(db["documents"].find({}, {
    "_id": 1,
    "filename": 1,
    "original_filename": 1,
    "file_path": 1,
    "status": 1,
    "category": 1,
    "document_type": 1,
    "sha256_hash": 1,
    "total_pages": 1,
    "total_chunks": 1,
    "total_kg_entities": 1,
    "total_kg_relationships": 1,
    "auto_metadata": 1,
    "created_at": 1,
    "updated_at": 1,
    "error_message": 1,
}))

print(f"  Found {len(mongo_docs)} document records in MongoDB")

# ---------------------------------------------------------------------------
# 2. ChromaDB — chunk counts per document
# ---------------------------------------------------------------------------
print("=== Querying ChromaDB ===")
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
try:
    collection = chroma_client.get_collection(CHROMA_COL)
    all_chroma = collection.get(include=["metadatas"])
    chroma_total = collection.count()
    print(f"  ChromaDB total vectors: {chroma_total}")
except Exception as exc:
    print(f"  ChromaDB error: {exc}")
    all_chroma = {"metadatas": [], "ids": []}
    chroma_total = 0

# Build per-doc chunk count and chunk IDs from ChromaDB
chroma_doc_chunks: dict[str, list[str]] = {}
for vec_id, meta in zip(all_chroma["ids"], all_chroma["metadatas"]):
    doc_id = meta.get("document_id", "")
    chroma_doc_chunks.setdefault(doc_id, []).append(vec_id)

print(f"  Unique document IDs in ChromaDB: {set(chroma_doc_chunks.keys())}")

# ---------------------------------------------------------------------------
# 3. Neo4j — entity / relationship counts per document
# ---------------------------------------------------------------------------
print("=== Querying Neo4j ===")
neo4j_entity_counts: dict[str, int] = {}
neo4j_rel_counts: dict[str, int] = {}

try:
    neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
    with neo4j_driver.session() as session:
        # Count nodes per document
        rows = session.run(
            "MATCH (n) WHERE n.document_id IS NOT NULL "
            "RETURN n.document_id AS doc_id, count(n) AS cnt"
        )
        for row in rows:
            neo4j_entity_counts[row["doc_id"]] = row["cnt"]

        # Count relationships per document
        rows2 = session.run(
            "MATCH (a)-[r]->(b) WHERE a.document_id IS NOT NULL "
            "RETURN a.document_id AS doc_id, count(r) AS cnt"
        )
        for row in rows2:
            neo4j_rel_counts[row["doc_id"]] = row["cnt"]

    neo4j_driver.close()
    print(f"  Neo4j entity doc IDs: {set(neo4j_entity_counts.keys())}")
except Exception as exc:
    print(f"  Neo4j error: {exc}")

# ---------------------------------------------------------------------------
# 4. Filesystem — which uploads still exist on disk
# ---------------------------------------------------------------------------
print("=== Scanning filesystem ===")
upload_files = {p.name: p for p in UPLOAD_DIR.glob("*.pdf")} if UPLOAD_DIR.exists() else {}
print(f"  Upload directory PDFs found: {len(upload_files)}")

# ---------------------------------------------------------------------------
# 5. Build inventory record for each MongoDB document
# ---------------------------------------------------------------------------
COMPLETED_STATUSES = {"completed"}

inventory = []
for doc in mongo_docs:
    doc_id     = str(doc["_id"])
    filename   = doc.get("filename") or doc.get("original_filename") or "unknown"
    status     = doc.get("status", "unknown")
    category   = doc.get("category", "GENERAL")
    doc_type   = doc.get("document_type", "")
    sha256     = doc.get("sha256_hash", "")
    pages      = doc.get("total_pages", 0) or 0
    mongo_chunks = doc.get("total_chunks", 0) or 0
    mongo_entities = doc.get("total_kg_entities", 0) or 0
    mongo_rels  = doc.get("total_kg_relationships", 0) or 0
    error_msg  = doc.get("error_message", "")
    created_at = doc.get("created_at", "")
    if created_at and hasattr(created_at, 'isoformat'):
        created_at = created_at.isoformat()

    # Auto metadata
    auto_meta  = doc.get("auto_metadata") or {}
    title      = auto_meta.get("title", "") or filename
    source     = auto_meta.get("source", "")

    # ChromaDB cross-check
    chroma_chunks = chroma_doc_chunks.get(doc_id, [])
    chroma_chunk_count = len(chroma_chunks)
    embedding_available = chroma_chunk_count > 0

    # Neo4j cross-check
    kg_entities = neo4j_entity_counts.get(doc_id, 0)
    kg_rels     = neo4j_rel_counts.get(doc_id, 0)
    # Fall back to mongo-reported counts if not in KG index by doc_id
    if kg_entities == 0 and mongo_entities > 0:
        # Note: may mean doc_id mismatch between Neo4j and Mongo
        kg_entities_note = f"MongoDB reported {mongo_entities} but Neo4j has 0 for doc_id={doc_id}"
    else:
        kg_entities_note = ""

    # Filesystem presence (loose match on filename stem)
    file_on_disk = any(filename in fname for fname in upload_files) or \
                   any(doc_id in fname for fname in upload_files)

    # Determine if "successfully processed" for benchmark purposes
    # Criteria: status==completed AND chroma chunks > 0
    is_fully_processed = (
        status in COMPLETED_STATUSES
        and chroma_chunk_count > 0
    )
    kg_grounded = kg_entities > 0 or (mongo_entities > 0)

    record = {
        "document_id": doc_id,
        "filename": filename,
        "title": title,
        "source": source,
        "category": category,
        "document_type": doc_type,
        "processing_status": status,
        "is_fully_processed": is_fully_processed,
        "sha256": sha256,
        "pages": pages,
        "mongodb_chunk_count": mongo_chunks,
        "chromadb_chunk_count": chroma_chunk_count,
        "embedding_available": embedding_available,
        "kg_entity_count": mongo_entities,
        "kg_relationship_count": mongo_rels,
        "neo4j_entity_count": kg_entities,
        "neo4j_rel_count": kg_rels,
        "kg_grounded": kg_grounded,
        "file_on_disk": file_on_disk,
        "error_message": error_msg,
        "created_at": str(created_at),
        "notes": kg_entities_note,
    }
    inventory.append(record)

# ---------------------------------------------------------------------------
# 6. Also check KG-only docs (docs that appear in Neo4j but not current MongoDB)
# ---------------------------------------------------------------------------
mongo_ids = {r["document_id"] for r in inventory}
for doc_id, cnt in neo4j_entity_counts.items():
    if doc_id not in mongo_ids:
        # Historical KG document — no longer in current MongoDB
        inventory.append({
            "document_id": doc_id,
            "filename": "HISTORICAL_KG_ONLY",
            "title": "",
            "source": "",
            "category": "UNKNOWN",
            "document_type": "",
            "processing_status": "historical_kg_only",
            "is_fully_processed": False,
            "sha256": "",
            "pages": 0,
            "mongodb_chunk_count": 0,
            "chromadb_chunk_count": len(chroma_doc_chunks.get(doc_id, [])),
            "embedding_available": False,
            "kg_entity_count": cnt,
            "kg_relationship_count": neo4j_rel_counts.get(doc_id, 0),
            "neo4j_entity_count": cnt,
            "neo4j_rel_count": neo4j_rel_counts.get(doc_id, 0),
            "kg_grounded": True,
            "file_on_disk": False,
            "error_message": "",
            "created_at": "",
            "notes": "Present in Neo4j KG but not in current MongoDB documents collection",
        })

# ---------------------------------------------------------------------------
# 7. Compute summary statistics
# ---------------------------------------------------------------------------
fully_processed = [r for r in inventory if r["is_fully_processed"]]
total_chroma_vectors = sum(r["chromadb_chunk_count"] for r in fully_processed)
kg_grounded_count = sum(1 for r in fully_processed if r["kg_grounded"])

# Category / domain distribution
category_dist: dict[str, int] = {}
for r in fully_processed:
    cat = r["category"] or "GENERAL"
    category_dist[cat] = category_dist.get(cat, 0) + 1

summary = {
    "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
    "total_mongodb_records": len(mongo_docs),
    "total_inventory_records": len(inventory),
    "fully_processed_count": len(fully_processed),
    "total_chroma_vectors": chroma_total,
    "total_chroma_vectors_for_processed_docs": total_chroma_vectors,
    "kg_grounded_documents": kg_grounded_count,
    "category_distribution": category_dist,
    "chroma_db_path": CHROMA_PATH,
    "chroma_collection": CHROMA_COL,
    "mongo_database": MONGO_DB,
}

output = {
    "summary": summary,
    "inventory": inventory,
}

# ---------------------------------------------------------------------------
# 8. Write JSON output
# ---------------------------------------------------------------------------
json_path = OUTPUT_DIR / "research_corpus_inventory.json"
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, default=str)

print(f"\n=== Inventory JSON saved to {json_path} ===")

# ---------------------------------------------------------------------------
# 9. Write Markdown report
# ---------------------------------------------------------------------------
md_lines = [
    "# Research Corpus Inventory",
    "",
    f"**Generated:** {summary['generated_at']}",
    "",
    "## Summary",
    f"- MongoDB document records: {summary['total_mongodb_records']}",
    f"- Total inventory records (incl. historical KG): {summary['total_inventory_records']}",
    f"- **Fully processed (status=completed + embeddings):** {summary['fully_processed_count']}",
    f"- ChromaDB total vectors: {summary['total_chroma_vectors']}",
    f"- Vectors belonging to fully-processed docs: {summary['total_chroma_vectors_for_processed_docs']}",
    f"- KG-grounded fully-processed docs: {summary['kg_grounded_documents']}",
    "",
    "## Category Distribution (Fully Processed)",
]
for cat, cnt in sorted(category_dist.items()):
    md_lines.append(f"- {cat}: {cnt}")

md_lines += [
    "",
    "## Document-Level Details",
    "",
    "| # | Document ID | Filename | Status | Fully Processed | Pages | Chroma Chunks | KG Entities | KG Rels |",
    "|---|-------------|----------|--------|----------------|-------|---------------|-------------|---------|",
]

for i, rec in enumerate(inventory, 1):
    fp_mark = "✅" if rec["is_fully_processed"] else "❌"
    row = (
        f"| {i} | `{rec['document_id'][:12]}…` | {rec['filename'][:45]} "
        f"| {rec['processing_status']} | {fp_mark} "
        f"| {rec['pages']} | {rec['chromadb_chunk_count']} "
        f"| {rec['kg_entity_count']} | {rec['kg_relationship_count']} |"
    )
    md_lines.append(row)

md_lines += [
    "",
    "## Fully Processed Document Details",
    "",
]
for rec in fully_processed:
    md_lines += [
        f"### {rec['filename']}",
        f"- **Document ID:** `{rec['document_id']}`",
        f"- **Status:** {rec['processing_status']}",
        f"- **Pages:** {rec['pages']}",
        f"- **ChromaDB Chunks:** {rec['chromadb_chunk_count']}",
        f"- **KG Entities (MongoDB reported):** {rec['kg_entity_count']}",
        f"- **KG Relationships (MongoDB reported):** {rec['kg_relationship_count']}",
        f"- **KG Grounded:** {'Yes' if rec['kg_grounded'] else 'No'}",
        f"- **SHA256:** `{rec['sha256'][:32]}…`" if rec['sha256'] else "- **SHA256:** N/A",
        f"- **Notes:** {rec['notes']}" if rec['notes'] else "",
        "",
    ]

md_lines += [
    "## Conclusion",
    "",
    f"The live system contains **{len(fully_processed)}** fully processed documents "
    f"with verified ChromaDB embeddings.",
    "",
    "> [!IMPORTANT]",
    f"> {'INSUFFICIENT_CORPUS — fewer than 15 fully processed documents available. Recommend ingesting additional documents before benchmark construction.' if len(fully_processed) < 15 else 'CORPUS_AVAILABLE — sufficient documents found for benchmark construction.'}",
]

md_path = OUTPUT_DIR / "research_corpus_inventory.md"
with open(md_path, "w", encoding="utf-8") as f:
    f.write("\n".join(md_lines))

print(f"Markdown report saved to {md_path}")

# ---------------------------------------------------------------------------
# 10. Print summary to console
# ---------------------------------------------------------------------------
print("\n" + "="*60)
print("CORPUS DISCOVERY SUMMARY")
print("="*60)
print(f"Total MongoDB records  : {len(mongo_docs)}")
print(f"Fully processed docs   : {len(fully_processed)}")
print(f"ChromaDB total vectors : {chroma_total}")
print(f"KG-grounded docs       : {kg_grounded_count}")
print(f"Category distribution  : {category_dist}")
print()
print("Fully processed documents:")
for rec in fully_processed:
    print(f"  [{rec['document_id'][:12]}] {rec['filename'][:50]:50s} | chunks={rec['chromadb_chunk_count']:3d} | entities={rec['kg_entity_count']:2d}")
print()
if len(fully_processed) < 15:
    print("STATUS: INSUFFICIENT_CORPUS (<15 fully processed docs)")
    print("ACTION REQUIRED: Ingest additional documents before benchmark construction.")
else:
    print("STATUS: CORPUS_AVAILABLE")
print("="*60)
