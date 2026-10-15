import argparse
import sys
import os
from pymongo import MongoClient
import chromadb
from bson import ObjectId

def repair_metadata(dry_run: bool):
    # Connect to MongoDB
    client_mongo = MongoClient("mongodb://localhost:27017")
    db = client_mongo["infra_knowledge"]
    docs_col = db["documents"]
    ws_docs_col = db["workspace_documents"]

    # Connect to ChromaDB
    client_chroma = chromadb.PersistentClient(path="./chroma_db")
    col = client_chroma.get_collection("infra_documents")
    
    results = col.get(include=["metadatas"])
    ids = results["ids"]
    metadatas = results["metadatas"] or []
    
    vectors_scanned = len(ids)
    vectors_requiring_repair = 0
    global_count = 0
    workspace_count = 0
    unresolved_count = 0
    would_modify = 0
    
    # Track document-level stats to report
    doc_reports = {}
    
    # We will collect the updates here
    updates = {"ids": [], "metadatas": []}

    for i, vector_id in enumerate(ids):
        m = metadatas[i] or {}
        doc_id = m.get("document_id")
        
        # Check if is_global is missing
        if "is_global" not in m:
            vectors_requiring_repair += 1
            
            if not doc_id:
                unresolved_count += 1
                doc_reports.setdefault("UNKNOWN", {"filename": m.get("filename", "UNKNOWN"), "vector_count": 0, "missing_metadata": 0, "status": "UNRESOLVED", "reason": "No document_id in chunk metadata"})
                doc_reports["UNKNOWN"]["vector_count"] += 1
                doc_reports["UNKNOWN"]["missing_metadata"] += 1
                continue
                
            # Initialize doc report if not exists
            if doc_id not in doc_reports:
                doc_reports[doc_id] = {
                    "filename": m.get("document_name") or m.get("filename") or m.get("source", "UNKNOWN"),
                    "vector_count": 0,
                    "missing_metadata": 0,
                    "scope": None,
                    "proposed_is_global": None,
                    "proposed_workspace_id": None,
                    "unresolved_count": 0,
                    "reason": ""
                }
                
                # Look it up in MongoDB once per doc_id
                try:
                    obj_id = ObjectId(doc_id)
                    global_doc = docs_col.find_one({"_id": obj_id})
                    if global_doc:
                        doc_reports[doc_id]["scope"] = "Global"
                        doc_reports[doc_id]["proposed_is_global"] = True
                        doc_reports[doc_id]["proposed_workspace_id"] = None
                    else:
                        ws_doc = ws_docs_col.find_one({"_id": obj_id})
                        if ws_doc:
                            doc_reports[doc_id]["scope"] = "Workspace"
                            doc_reports[doc_id]["proposed_is_global"] = False
                            doc_reports[doc_id]["proposed_workspace_id"] = str(ws_doc.get("workspace_id"))
                        else:
                            doc_reports[doc_id]["scope"] = "UNRESOLVED"
                            doc_reports[doc_id]["reason"] = "Not found in MongoDB documents or workspace_documents"
                except Exception as e:
                    doc_reports[doc_id]["scope"] = "UNRESOLVED"
                    doc_reports[doc_id]["reason"] = f"Invalid ObjectId or Mongo error: {str(e)}"
            
            report = doc_reports[doc_id]
            report["vector_count"] += 1
            report["missing_metadata"] += 1
            
            if report["scope"] == "Global":
                global_count += 1
                would_modify += 1
                new_m = m.copy()
                new_m["is_global"] = True
                updates["ids"].append(vector_id)
                updates["metadatas"].append(new_m)
            elif report["scope"] == "Workspace":
                workspace_count += 1
                would_modify += 1
                new_m = m.copy()
                new_m["is_global"] = False
                new_m["workspace_id"] = report["proposed_workspace_id"]
                updates["ids"].append(vector_id)
                updates["metadatas"].append(new_m)
            else:
                unresolved_count += 1
                report["unresolved_count"] += 1

    print("=== ChromaDB Metadata Repair ===")
    print(f"Vectors scanned: {vectors_scanned}")
    print(f"Vectors requiring repair: {vectors_requiring_repair}")
    print(f"Global: {global_count}")
    print(f"Workspace: {workspace_count}")
    print(f"Unable to resolve: {unresolved_count}")
    print(f"Would modify: {would_modify}\n")
    
    print("--- Document-Level Details ---")
    for doc_id, r in doc_reports.items():
        print(f"Document ID: {doc_id}")
        print(f"  Filename: {r['filename']}")
        print(f"  Vectors: {r['vector_count']} (Missing metadata: {r['missing_metadata']})")
        print(f"  MongoDB scope: {r['scope']}")
        print(f"  Proposed is_global: {r['proposed_is_global']}")
        print(f"  Proposed workspace_id: {r['proposed_workspace_id']}")
        if r['unresolved_count'] > 0:
            print(f"  Unresolved count: {r['unresolved_count']}")
            print(f"  Reason: {r['reason']}")
        print("")

    if dry_run:
        print("[DRY RUN] No changes were made to ChromaDB.")
    else:
        if updates["ids"]:
            print(f"Executing update for {len(updates['ids'])} vectors...")
            # We must use update() to just modify metadatas without modifying embeddings or documents
            # Because update requires embeddings/documents if we want to change them, but if we don't pass them, it only updates metadatas.
            # Let's verify ChromaDB update syntax.
            # collection.update(ids=..., metadatas=...)
            # To be safe and batch it:
            batch_size = 100
            for i in range(0, len(updates["ids"]), batch_size):
                col.update(
                    ids=updates["ids"][i:i+batch_size],
                    metadatas=updates["metadatas"][i:i+batch_size]
                )
            print("[SUCCESS] ChromaDB metadata repaired successfully.")
        else:
            print("No vectors required repair.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Repair ChromaDB metadata")
    parser.add_argument("--dry-run", action="store_true", help="Calculate repairs without modifying the database")
    parser.add_argument("--execute", action="store_true", help="Execute the repair and modify the database")
    args = parser.parse_args()
    
    if args.execute and args.dry_run:
        print("Error: Cannot specify both --dry-run and --execute")
        sys.exit(1)
        
    if not args.execute and not args.dry_run:
        print("Error: Must explicitly specify --dry-run or --execute")
        parser.print_help()
        sys.exit(1)
        
    repair_metadata(args.dry_run)
