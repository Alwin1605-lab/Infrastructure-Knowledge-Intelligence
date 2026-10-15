import os
import chromadb
from collections import defaultdict

def audit_metadata():
    client = chromadb.PersistentClient(path="./chroma_db")
    col = client.get_collection("infra_documents")
    
    # Retrieve all chunks
    results = col.get(include=["metadatas"])
    metadatas = results["metadatas"] or []
    
    total_vectors = len(metadatas)
    has_is_global = 0
    missing_is_global = 0
    is_global_true = 0
    is_global_false = 0
    
    has_workspace = 0
    missing_workspace = 0
    
    missing_document_id = 0
    missing_chunk_index = 0
    missing_page_number = 0
    missing_filename = 0
    
    doc_stats = defaultdict(lambda: {
        "count": 0,
        "missing_is_global": 0,
        "missing_workspace_id": 0,
        "missing_page": 0
    })
    
    for m in metadatas:
        if m is None:
            m = {}
            
        doc_id = m.get("document_id", "UNKNOWN")
        doc_stats[doc_id]["count"] += 1
        
        if "is_global" in m:
            has_is_global += 1
            if m["is_global"]:
                is_global_true += 1
            else:
                is_global_false += 1
        else:
            missing_is_global += 1
            doc_stats[doc_id]["missing_is_global"] += 1
            
        if "workspace_id" in m:
            has_workspace += 1
        else:
            missing_workspace += 1
            doc_stats[doc_id]["missing_workspace_id"] += 1
            
        if "document_id" not in m:
            missing_document_id += 1
            
        if "chunk_index" not in m:
            missing_chunk_index += 1
            
        if "page_number" not in m:
            missing_page_number += 1
            doc_stats[doc_id]["missing_page"] += 1
            
        if "document_name" not in m and "filename" not in m and "source" not in m:
            missing_filename += 1

    os.makedirs("experiments/v2", exist_ok=True)
    with open("experiments/v2/production_metadata_audit.md", "w", encoding="utf-8") as f:
        f.write("# Production Metadata Audit\n\n")
        f.write("## Overall Statistics\n")
        f.write(f"- **Total vectors**: {total_vectors}\n")
        f.write(f"- **Vectors with is_global**: {has_is_global}\n")
        f.write(f"- **Vectors missing is_global**: {missing_is_global}\n")
        f.write(f"- **is_global=true**: {is_global_true}\n")
        f.write(f"- **is_global=false**: {is_global_false}\n")
        f.write(f"- **Vectors with workspace_id**: {has_workspace}\n")
        f.write(f"- **Vectors missing workspace_id**: {missing_workspace}\n")
        f.write(f"- **Missing document_id**: {missing_document_id}\n")
        f.write(f"- **Missing chunk_index**: {missing_chunk_index}\n")
        f.write(f"- **Missing page_number**: {missing_page_number}\n")
        f.write(f"- **Missing filename/source**: {missing_filename}\n\n")
        
        f.write("## Document-Level Statistics\n")
        f.write("| Document ID | Total Vectors | Missing `is_global` | Missing `workspace_id` | Missing `page_number` |\n")
        f.write("|-------------|---------------|---------------------|------------------------|-----------------------|\n")
        for doc_id, stats in doc_stats.items():
            f.write(f"| {doc_id} | {stats['count']} | {stats['missing_is_global']} | {stats['missing_workspace_id']} | {stats['missing_page']} |\n")
            
    print("Audit complete! Report saved to experiments/v2/production_metadata_audit.md")

if __name__ == "__main__":
    audit_metadata()
