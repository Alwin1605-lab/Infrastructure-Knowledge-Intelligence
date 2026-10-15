import json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))
import chromadb
from app.config import get_settings
from neo4j import GraphDatabase

def validate_ground_truth():
    settings = get_settings()
    chroma_client = chromadb.PersistentClient(path="./chroma_db")
    col = chroma_client.get_collection(settings.CHROMADB_COLLECTION)
    
    neo4j_uri = settings.NEO4J_URI.replace("neo4j:7687", "localhost:7687")
    try:
        neo4j_driver = GraphDatabase.driver(neo4j_uri, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD))
    except Exception:
        neo4j_driver = None

    with open("experiments/v2/corrected_benchmark_questions.json", "r", encoding="utf-8") as f:
        questions = json.load(f)

    report_lines = ["# Ground Truth Validation Report\n"]
    
    valid_count = 0
    total_count = len(questions)
    
    for q in questions:
        q_id = q["question_id"]
        report_lines.append(f"## {q_id}")
        
        if not q.get("is_valid"):
            report_lines.append("Status: INVALID (Excluded during reconstruction)\n")
            continue
            
        gt = q["ground_truth"]
        
        # 1. Chunk exists and matches evidence
        chunk_id = gt["chunks"][0]
        res = col.get(ids=[chunk_id], include=["documents", "metadatas"])
        
        if not res["ids"]:
            report_lines.append(f"Status: INVALID - Chunk {chunk_id} not found in ChromaDB\n")
            continue
            
        stored_text = res["documents"][0]
        stored_meta = res["metadatas"][0]
        expected_text = gt["evidence"][0]
        
        if stored_text != expected_text:
            report_lines.append("Status: INVALID - Evidence text does not perfectly match stored chunk\n")
            continue
            
        if stored_meta.get("document_id") != gt["documents"][0]:
            report_lines.append("Status: INVALID - Chunk does not belong to expected document ID\n")
            continue
            
        # 2. Check entities if Neo4j is available
        entities_valid = True
        if neo4j_driver and gt.get("entities"):
            with neo4j_driver.session() as session:
                for ent_id in gt["entities"]:
                    result = session.run("MATCH (n) WHERE n.id = $id RETURN count(n) as c", id=ent_id).single()["c"]
                    if result == 0:
                        entities_valid = False
                        break
        if not entities_valid:
            report_lines.append("Status: INVALID - Expected entities not found in Neo4j\n")
            continue
            
        report_lines.append("Status: VALIDATED\n")
        valid_count += 1
        
    report_lines.append("## Summary\n")
    report_lines.append(f"Required final metric: {valid_count} / {total_count}\n")
    
    with open("experiments/v2/ground_truth_validation_report.md", "w", encoding="utf-8") as f:
        f.writelines(report_lines)
        
    print(f"Validation complete: {valid_count} / {total_count} validated.")

if __name__ == "__main__":
    validate_ground_truth()
