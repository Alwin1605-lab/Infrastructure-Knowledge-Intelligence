import json
import chromadb
from datetime import datetime
import os

def backup_metadata():
    client = chromadb.PersistentClient(path="./chroma_db")
    col = client.get_collection("infra_documents")
    
    results = col.get(include=["metadatas"])
    
    ids = results["ids"]
    metadatas = results["metadatas"]
    
    backup_data = {
        "collection_name": "infra_documents",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "vector_count": len(ids),
        "backup_script_version": "1.0",
        "vectors": []
    }
    
    for i, vector_id in enumerate(ids):
        meta = metadatas[i] or {}
        backup_data["vectors"].append({
            "id": vector_id,
            "document_id": meta.get("document_id"),
            "chunk_index": meta.get("chunk_index"),
            "metadata": meta,
            "filename": meta.get("document_name") or meta.get("filename") or meta.get("source"),
            "page_number": meta.get("page_number")
        })
        
    os.makedirs("experiments/v2", exist_ok=True)
    timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_path = f"experiments/v2/chroma_metadata_backup_{timestamp_str}.json"
    
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(backup_data, f, indent=2)
        
    print(f"Backup created at: {backup_path}")
    print(f"Backed up {len(ids)} vectors.")

if __name__ == "__main__":
    backup_metadata()
