import json
import os
import pymongo
from collections import defaultdict
from pathlib import Path

def discover_corpus():
    print("Discovering real research corpus from runtime databases...")
    
    # Connect to MongoDB
    mongo = pymongo.MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=2000)
    db = mongo["infra_knowledge"]
    docs_collection = db["documents"]
    
    # Only get completed documents
    completed_docs = list(docs_collection.find({"status": "completed"}))
    
    corpus_inventory = []
    category_counts = defaultdict(int)
    
    for doc in completed_docs:
        doc_info = {
            "document_id": str(doc["_id"]),
            "filename": doc.get("filename", "Unknown"),
            "category": doc.get("category", "GENERAL"),
            "source": "knowledge_base",
            "page_count": doc.get("total_pages", 0),
            "chunks": doc.get("chunks", 0),
            "kg_entities": doc.get("entities", 0),
            "kg_relationships": doc.get("relationships", 0),
            "processing_status": doc.get("status")
        }
        corpus_inventory.append(doc_info)
        category_counts[doc_info["category"]] += 1
        
    print(f"Found {len(corpus_inventory)} completed documents in MongoDB.")
    
    # Generate JSON
    with open("research_corpus_inventory.json", "w", encoding="utf-8") as f:
        json.dump(corpus_inventory, f, indent=2)
        
    # Generate MD
    md_content = [
        "# Research Corpus Inventory",
        "",
        "This inventory contains ONLY documents that have been completely processed and verified in the knowledge base.",
        "",
        "## Summary",
        f"- **Total Documents:** {len(corpus_inventory)}",
        "",
        "## Category Distribution"
    ]
    
    for cat, count in category_counts.items():
        md_content.append(f"- {cat}: {count}")
        
    md_content.extend([
        "",
        "## Documents",
        "| Filename | Category | Pages | Chunks | Entities | Relationships |",
        "|----------|----------|-------|--------|----------|---------------|"
    ])
    
    for doc in corpus_inventory:
        md_content.append(f"| {doc['filename']} | {doc['category']} | {doc['page_count']} | {doc['chunks']} | {doc['kg_entities']} | {doc['kg_relationships']} |")
        
    with open("research_corpus_inventory.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md_content))
        
    print("Generated research_corpus_inventory.json and research_corpus_inventory.md")

if __name__ == "__main__":
    discover_corpus()
