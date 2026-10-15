import json
import asyncio
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    print("Generating Baseline...")
    
    mongo_client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = mongo_client.infra_knowledge
    
    # Calculate baseline from DB
    documents_cursor = db.documents.find()
    
    documents = []
    total_chunks = 0
    total_entities = 0
    total_relationships = 0
    
    completed_docs = 0
    failed_docs = 0
    partial_docs = 0
    
    async for doc in documents_cursor:
        status = doc.get("status", "unknown")
        
        if status == "completed":
            completed_docs += 1
        elif status == "failed":
            failed_docs += 1
        elif status in ["partial", "rate_limited", "timeout"]:
            partial_docs += 1
            
        chunks = doc.get("total_chunks", 0)
        entities = doc.get("total_kg_entities", 0)
        rels = doc.get("total_kg_relationships", 0)
        
        total_chunks += chunks
        total_entities += entities
        total_relationships += rels
        
        documents.append({
            "filename": doc.get("filename"),
            "status": status,
            "chunks": chunks,
            "entities": entities,
            "relationships": rels
        })
        
    baseline_data = {
        "generated_at": datetime.utcnow().isoformat(),
        "total_documents_processed": len(documents),
        "completed": completed_docs,
        "failed": failed_docs,
        "partial": partial_docs,
        "total_chunks": total_chunks,
        "total_kg_entities": total_entities,
        "total_kg_relationships": total_relationships,
        "documents": documents
    }
    
    with open("knowledge_base_baseline.json", "w", encoding="utf-8") as f:
        json.dump(baseline_data, f, indent=2)
        
    with open("knowledge_base_baseline.md", "w", encoding="utf-8") as f:
        f.write("# Knowledge Base Runtime Baseline\n\n")
        f.write(f"- **Total Documents in DB:** {len(documents)}\n")
        f.write(f"- **Completed Successfully:** {completed_docs}\n")
        f.write(f"- **Failed:** {failed_docs}\n")
        f.write(f"- **Partial/Rate Limited:** {partial_docs}\n")
        f.write(f"- **Total Chunks (ChromaDB):** {total_chunks}\n")
        f.write(f"- **Total Entities (Neo4j):** {total_entities}\n")
        f.write(f"- **Total Relationships (Neo4j):** {total_relationships}\n")
        
    print(f"Baseline generated: {completed_docs} completed, {total_chunks} chunks, {total_entities} entities.")

    # Generate research config and baseline
    research_config = {
        "rag_chunk_size": 1000,
        "rag_chunk_overlap": 200,
        "embedding_model": "all-MiniLM-L6-v2",
        "llm_model": "llama-3.1-8b-instant",
        "kg_batch_size": 5
    }
    
    with open("research_experiment_config.json", "w", encoding="utf-8") as f:
        json.dump(research_config, f, indent=2)
        
    research_baseline = {
        "config": research_config,
        "baseline_metrics": baseline_data
    }
    
    with open("research_baseline.json", "w", encoding="utf-8") as f:
        json.dump(research_baseline, f, indent=2)
        
if __name__ == "__main__":
    asyncio.run(main())
