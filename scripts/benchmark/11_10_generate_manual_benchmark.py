import json
import chromadb

def generate_benchmark():
    client = chromadb.PersistentClient(path='./chroma_db')
    col = client.get_collection('infra_documents')
    results = col.get()
    
    questions = []
    
    docs_seen = set()
    
    q_id = 1
    for i, (doc, meta) in enumerate(zip(results['documents'], results['metadatas'])):
        doc_name = meta.get('filename', meta.get('document_id', 'unknown'))
        if doc_name in docs_seen:
            continue
            
        if len(doc) > 100:
            docs_seen.add(doc_name)
            
            words = doc.split()
            topic = " ".join(words[:15]).replace(".", "").replace(",", "")
            
            q = {
                "id": f"Q{q_id}",
                "category": "factual",
                "difficulty": "medium",
                "question": f"What is discussed in the section covering '{topic}'?",
                "ground_truth_documents": [doc_name],
                "ground_truth_evidence": [doc[:200] + "..."],
                "ground_truth_entities": [],
                "expected_answer_points": [topic],
                "source_pages": [meta.get("page_number", 1)]
            }
            questions.append(q)
            q_id += 1
            
        if len(questions) >= 6:
            break
            
    with open("benchmark_questions.json", "w", encoding="utf-8") as f:
        json.dump(questions, f, indent=2)
        
    print(f"Generated {len(questions)} grounded benchmark questions.")

if __name__ == "__main__":
    generate_benchmark()
