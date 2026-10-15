"""
Prioritized ingestion list for Phase 13.

Based on the 13_01_discover_corpus.py results, this script:
  1. Shows the recoverable LEDG document (has 237 chunks in ChromaDB, needs KG fix)
  2. Lists the 20 acquired_documents titles as ingest candidates
  3. Provides domain-priority recommendations
"""

import sys
import json
from pathlib import Path
from pymongo import MongoClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

MONGO_URI = "mongodb://localhost:27017"
MONGO_DB  = "infra_knowledge"
OUTPUT_DIR = Path("./experiments/v3")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]

print("=" * 70)
print("PHASE 13 — CORPUS STATUS & INGESTION PRIORITY REPORT")
print("=" * 70)

# --- Currently fully processed (ChromaDB embeddings confirmed) ---
fully_processed_ids = [
    "6a7990b8c902988cd052c9d3",  # DRCS Cover
    "6a79a3b8ca0dbb46c36a02d6",  # test_building_report
    "6a79a3f88ad17e8f86e6c72a",  # G01 facilities
    "6a79a41a08ca0700b6046c74",  # New Building Services Template
    "6a79a455976f591cd07e5757",  # gurugram pages
    "6a79a4acc42349d6271bf3cd",  # viga-and-corbel-inspection
]
print(f"\n[OK] Fully processed (embeddings in ChromaDB): {len(fully_processed_ids)}")

# --- LEDG: recoverable ---
print(f"\n[WARN] RECOVERABLE (embeddings present, KG indexing failed):")
print(f"   0-LEDG-v.1.0-120224.pdf  |  237 chunks  |  status=indexing_kg")
print(f"   Action: Update status to 'completed' to include in corpus")
print(f"   Note: 123-page Learning Environments Design Guidelines document")

# --- acquired_documents titles for ingestion ---
acq_docs = list(db["acquired_documents"].find({}, {"_id": 1, "title": 1, "category": 1, "source_url": 1}))
print(f"\n[LIST] acquired_documents available for ingestion: {len(acq_docs)}")
for d in acq_docs:
    title_safe = d.get("title", "N/A")[:70].encode("ascii", "replace").decode("ascii")
    print(f"   [{str(d['_id'])}] {title_safe}")

# --- Prioritization table ---
priority_list = [
    {"priority": 1, "domain": "Structural Engineering / Concrete",
     "recommendation": "Concrete Carbonation and Durability series (titles in acquired_docs)",
     "action": "Ingest from acquired_documents or upload new PDFs"},
    {"priority": 2, "domain": "Inspection / Maintenance",
     "recommendation": "Additional building inspection reports",
     "action": "Upload additional PDF inspection reports"},
    {"priority": 3, "domain": "Repair / Rehabilitation",
     "recommendation": "Corbel/viga follow-on documents; repair manuals",
     "action": "Upload repair & rehabilitation manuals"},
    {"priority": 4, "domain": "Construction / Methods",
     "recommendation": "Building construction procedure docs",
     "action": "Upload construction method statements"},
    {"priority": 5, "domain": "Geotechnical / Fire / Safety",
     "recommendation": "Add at least one doc each if available",
     "action": "Upload geotechnical or fire-safety documents"},
]

print("\n[PRIORITY] DOMAIN PRIORITY FOR INGESTION")
print("-" * 70)
for p in priority_list:
    print(f"  P{p['priority']}: {p['domain']}")
    print(f"       -> {p['recommendation']}")
    print(f"       -> ACTION: {p['action']}")
    print()

# --- Save as JSON ---
report = {
    "fully_processed_count": len(fully_processed_ids),
    "fully_processed_ids": fully_processed_ids,
    "recoverable_documents": [
        {
            "document_id": "6a7812eed03ebe1c6f5851dc",
            "filename": "0-LEDG-v.1.0-120224.pdf",
            "chromadb_chunks": 237,
            "pages": 123,
            "issue": "KG indexing failed (Settings.embed_documents attribute error)",
            "recovery_action": "Mark status=completed since embeddings exist; skip KG for now"
        }
    ],
    "acquired_documents_count": len(acq_docs),
    "acquired_document_titles": [d.get("title", "") for d in acq_docs],
    "domain_priority": priority_list,
    "recommendation": (
        "INSUFFICIENT_CORPUS: Only 6 fully processed documents with embeddings. "
        "LEDG is recoverable (237 chunks already indexed). "
        "Suggest: (1) Mark LEDG completed, (2) ingest ~10-15 additional domain-diverse PDFs "
        "to reach 15-20 fully processed documents before benchmark construction."
    )
}

out_path = OUTPUT_DIR / "ingestion_priority_list.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, default=str)

print(f"Priority list saved to: {out_path}")
print()
print("STATUS: INSUFFICIENT_CORPUS")
print("Minimum recommended before benchmark: 15 documents")
print("Current fully-processed with embeddings: 6")
print("LEDG recoverable: +1 (237 chunks)")
print("Need at minimum: ~8 more documents ingested")
