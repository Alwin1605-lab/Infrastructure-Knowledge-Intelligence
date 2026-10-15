import json
import asyncio
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from app.config import get_settings
from app.embedding.huggingface import HuggingFaceEmbeddingService
import chromadb
from neo4j import GraphDatabase

async def main():
    print("Rebuilding Ground Truth...")
    settings = get_settings()
    
    # Load original benchmark questions
    with open("benchmark_questions.json", "r", encoding="utf-8") as f:
        original_questions = json.load(f)
        
    e_service = HuggingFaceEmbeddingService(settings)
    
    # Use exact same chroma connection as the experiment adapter
    chroma_client = chromadb.PersistentClient(path="./chroma_db")
    col = chroma_client.get_collection(settings.CHROMADB_COLLECTION)
    
    neo4j_uri = settings.NEO4J_URI.replace("neo4j:7687", "localhost:7687")
    try:
        neo4j_driver = GraphDatabase.driver(neo4j_uri, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD))
    except Exception:
        neo4j_driver = None

    corrected_benchmark = []
    
    for i, q_data in enumerate(original_questions):
        q_id = f"Q{i+1}"
        q_text = q_data["question"]
        expected_points = q_data.get("expected_answer_points", [])
        
        print(f"Processing {q_id}: {q_text[:50]}...")
        
        # We need to find if the expected answer points actually exist in the DB.
        # We'll embed the question or the expected point itself to find the most likely source chunk.
        search_query = expected_points[0] if expected_points else q_text
        query_embedding = await e_service.embed_text(search_query)
        
        results = col.query(
            query_embeddings=[query_embedding],
            n_results=1,
            include=["documents", "metadatas", "distances"]
        )
        
        is_valid = False
        rebuilt_gt = None
        
        if results["ids"] and results["ids"][0]:
            doc_id = results["metadatas"][0][0].get("document_id")
            chunk_text = results["documents"][0][0]
            dist = results["distances"][0][0]
            score = 1.0 - (dist / 2.0)
            
            # Very high similarity means we found the exact chunk it was derived from
            if score > 0.8:
                is_valid = True
                meta = results["metadatas"][0][0]
                
                rebuilt_gt = {
                    "documents": [doc_id],
                    "chunks": [results["ids"][0][0]],
                    "pages": [meta.get("page_number")],
                    "evidence": [chunk_text],
                    "answer_points": [search_query], # using the point we searched for
                    "entities": [],
                    "relationships": []
                }
                
                # Optionally check Neo4j for entities from this document
                if neo4j_driver:
                    with neo4j_driver.session() as session:
                        entities = session.run(
                            "MATCH (n) WHERE n.source_document = $doc RETURN n.id as id LIMIT 2",
                            doc=meta.get("document_name")
                        )
                        rebuilt_gt["entities"] = [record["id"] for record in entities]
        
        if is_valid:
            print(f"  -> VALID. Found chunk in {meta.get('document_name')}")
            corrected_benchmark.append({
                "question_id": q_id,
                "question": q_text,
                "ground_truth": rebuilt_gt,
                "is_valid": True
            })
        else:
            print(f"  -> INVALID. Could not ground in actual corpus.")
            corrected_benchmark.append({
                "question_id": q_id,
                "question": q_text,
                "ground_truth": None,
                "is_valid": False,
                "exclusion_reason": "Missing from infra_documents corpus"
            })
            
    os.makedirs("experiments/v2", exist_ok=True)
    with open("experiments/v2/corrected_benchmark_questions.json", "w", encoding="utf-8") as f:
        json.dump(corrected_benchmark, f, indent=2)
        
    print(f"\nRebuilt {len([q for q in corrected_benchmark if q['is_valid']])}/{len(corrected_benchmark)} valid questions.")

if __name__ == "__main__":
    asyncio.run(main())
