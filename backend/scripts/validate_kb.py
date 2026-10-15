import asyncio
import os
import sys
import json
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.config import get_settings
from app.models.document import Document, DocumentStatus
import chromadb

async def validate_knowledge_base():
    settings = get_settings()
    
    # Init MongoDB
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    await init_beanie(database=client[settings.MONGODB_DATABASE], document_models=[Document])
    
    # Init ChromaDB
    chroma_client = chromadb.HttpClient(host=settings.CHROMADB_HOST, port=settings.CHROMADB_PORT)
    try:
        collection = chroma_client.get_collection(settings.CHROMADB_COLLECTION)
        chroma_count = collection.count()
    except Exception:
        chroma_count = 0

    # Init Neo4j
    kg_service = KnowledgeGraphService()

    print("Starting Knowledge Base Validation...\n")
    
    docs = await Document.find_all().to_list()
    total_docs = len(docs)
    
    categories = {}
    completed_docs = 0
    total_chunks = 0
    total_entities = 0
    total_relationships = 0
    duplicate_count = 0
    
    for doc in docs:
        cat = doc.document_type.value if hasattr(doc.document_type, 'value') else str(doc.document_type)
        categories[cat] = categories.get(cat, 0) + 1
        
        if doc.status == DocumentStatus.COMPLETED:
            completed_docs += 1
            
        if doc.metadata and getattr(doc.metadata, 'is_duplicate', False):
            duplicate_count += 1
            
        total_chunks += len(doc.extracted_pages) if hasattr(doc, 'extracted_pages') and doc.extracted_pages else 0
        total_entities += getattr(doc, 'total_kg_entities', 0) or 0
        total_relationships += getattr(doc, 'total_kg_relationships', 0) or 0
        
    print(f"Total Documents in MongoDB: {total_docs}")
    print(f"Total Completed Documents: {completed_docs}")
    print(f"Total Duplicates Detected: {duplicate_count}")
    print(f"Total Vectors in ChromaDB: {chroma_count}")
    print(f"Total Chunks in MongoDB: {total_chunks}")
    
    print("\nDocument Category Coverage:")
    for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {cat}: {count} ({(count/max(1, total_docs))*100:.1f}%)")
        
    print(f"\nNeo4j Knowledge Graph:")
    print(f"  - Total Entities: {total_entities}")
    print(f"  - Total Relationships: {total_relationships}")
    if total_entities > 0:
        print(f"  - Graph Connectivity (Rel/Entity): {total_relationships/total_entities:.2f}")
    if total_chunks > 0:
        print(f"  - Entity Density (Entities/Chunk): {total_entities/total_chunks:.2f}")
        
    print("\nActionable Coverage Recommendations:")
    targets = {
        "research_paper": 50,
        "engineering_standard": 5,
        "CPWD Manual": 3,
        "NBC": 3,
        "inspection_report": 5,
        "technical_data_sheet": 10,
        "product_manual": 10
    }
    
    missing = []
    for target_cat, required in targets.items():
        current = categories.get(target_cat, 0)
        if current < required:
            missing.append(f"Need {required - current} more {target_cat} documents (Current: {current}/{required})")
            
    if missing:
        for m in missing:
            print(f"  [RECOMMENDATION] {m}")
    else:
        print("  ✅ All coverage targets met!")
        
    # Write report
    report = f"""# Knowledge Base Validation & Coverage Report

## Overall Metrics
- **Total Documents**: {total_docs}
- **Successfully Processed**: {completed_docs}
- **Duplicate Rate**: {(duplicate_count/max(1, total_docs))*100:.1f}%
- **Total Chunks (Vector Store)**: {chroma_count}

## Knowledge Graph Metrics
- **Total Entities**: {total_entities}
- **Total Relationships**: {total_relationships}
- **Entity Density**: {total_entities/max(1, total_chunks):.2f} entities per chunk
- **Graph Connectivity**: {total_relationships/max(1, total_entities):.2f} relationships per entity

## Coverage by Domain
"""
    for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        report += f"- **{cat}**: {count} documents\n"
        
    report += "\n## Recommendations\n"
    if missing:
        for m in missing:
            report += f"- {m}\n"
    else:
        report += "- ✅ All targets met.\n"
        
    with open("knowledge_coverage_report.md", "w") as f:
        f.write(report)
        
    print("\nGenerated knowledge_coverage_report.md")
    
if __name__ == "__main__":
    asyncio.run(validate_knowledge_base())
