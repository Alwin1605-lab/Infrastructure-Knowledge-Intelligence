import os
import glob
import json
import hashlib
import asyncio
from typing import Dict, Any

try:
    import PyPDF2
except ImportError:
    pass

from motor.motor_asyncio import AsyncIOMotorClient

async def get_db_status(sha256: str, db) -> Dict[str, Any]:
    # Query mongo
    doc = await db.documents.find_one({"sha256_hash": sha256})
    job = await db.processing_jobs.find_one({"document_id": str(doc["_id"]) if doc else None})
    
    return {
        "mongodb_status": doc["status"] if doc else "NOT_FOUND",
        "processing_job_status": job["status"] if job else "NOT_FOUND",
        "processing_job_step": job["current_step"] if job else "NOT_FOUND",
        "chromadb_status": "INDEXED" if doc and doc.get("total_chunks", 0) > 0 else "NOT_INDEXED",
        "neo4j_status": "INDEXED" if doc and doc.get("total_kg_entities", 0) > 0 else "NOT_INDEXED",
        "total_chunks": doc.get("total_chunks", 0) if doc else 0,
        "total_kg_entities": doc.get("total_kg_entities", 0) if doc else 0,
        "total_kg_relationships": doc.get("total_kg_relationships", 0) if doc else 0,
    }

def get_page_count(filepath: str) -> int:
    try:
        with open(filepath, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            return len(reader.pages)
    except Exception:
        return 0

def discover_directories():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # Known project directories
    dirs = [
        os.path.join(base_dir, "knowledge_base"),
        os.path.join(base_dir, "uploads"),
        os.path.join(base_dir, "backend", "uploads"),
    ]
    # Check docker-compose.yml for volume mounts
    try:
        with open(os.path.join(base_dir, "docker-compose.yml"), "r") as f:
            for line in f:
                if "./" in line and ":" in line and "volume" in line.lower():
                    # extract path
                    parts = line.strip().split(":")
                    path = parts[0].replace("-", "").strip()
                    if path.startswith("./"):
                        full_path = os.path.join(base_dir, path[2:])
                        if full_path not in dirs:
                            dirs.append(full_path)
    except Exception:
        pass
        
    return [d for d in dirs if os.path.exists(d)]

async def main():
    print("Discovering Knowledge Base...")
    
    mongo_client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = mongo_client.infra_knowledge
    
    dirs = discover_directories()
    inventory = []
    
    for d in dirs:
        for root, _, files in os.walk(d):
            for file in files:
                if file.lower().endswith('.pdf'):
                    filepath = os.path.join(root, file)
                    rel_path = os.path.relpath(filepath, os.path.dirname(os.path.abspath(__file__)))
                    
                    with open(filepath, 'rb') as f:
                        file_content = f.read()
                        sha256 = hashlib.sha256(file_content).hexdigest()
                        
                    file_size = os.path.getsize(filepath)
                    pages = get_page_count(filepath)
                    
                    db_status = await get_db_status(sha256, db)
                    
                    inventory.append({
                        "filename": file,
                        "relative_path": rel_path,
                        "sha256": sha256,
                        "file_size": file_size,
                        "page_count": pages,
                        "category": "RESEARCH" if "research" in rel_path.lower() else "GENERAL",
                        **db_status
                    })
                    
    # Save JSON
    with open("knowledge_base_inventory.json", "w", encoding="utf-8") as f:
        json.dump(inventory, f, indent=2)
        
    # Save Markdown
    with open("knowledge_base_inventory.md", "w", encoding="utf-8") as f:
        f.write("# Knowledge Base Inventory\n\n")
        f.write("| Filename | Pages | Status | Job Step | Chunks | KG Entities |\n")
        f.write("|----------|-------|--------|----------|--------|-------------|\n")
        for item in inventory:
            f.write(f"| {item['filename']} | {item['page_count']} | {item['mongodb_status']} | {item['processing_job_step']} | {item['total_chunks']} | {item['total_kg_entities']} |\n")

    print(f"Discovered {len(inventory)} PDFs.")
    
if __name__ == "__main__":
    asyncio.run(main())
