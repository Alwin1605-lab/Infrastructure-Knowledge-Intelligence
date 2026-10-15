import json
import os

def validate_benchmark():
    print("Validating benchmark questions...")
    
    if not os.path.exists("benchmark_questions.json"):
        print("Missing benchmark_questions.json")
        return
        
    if not os.path.exists("research_corpus.json"):
        print("Missing research_corpus.json")
        return
        
    with open("benchmark_questions.json", "r", encoding="utf-8") as f:
        questions = json.load(f)
        
    with open("research_corpus.json", "r", encoding="utf-8") as f:
        corpus = json.load(f)
        
    valid_docs = {doc["filename"] for doc in corpus["selected_documents"]} | {doc["document_id"] for doc in corpus["selected_documents"]}
    
    report = [
        "# Benchmark Validation Report",
        "",
        f"**Total Questions:** {len(questions)}",
        ""
    ]
    
    errors = []
    
    for q in questions:
        for doc in q.get("ground_truth_documents", []):
            if doc not in valid_docs:
                errors.append(f"Question {q['id']} references invalid/missing document: {doc}")
                
    if not errors:
        report.append("## Status: PASS")
        report.append("All questions map to valid, successfully processed documents.")
    else:
        report.append("## Status: FAIL")
        for e in errors:
            report.append(f"- {e}")
            
    with open("benchmark_validation_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report))
        
    print(f"Validation complete. Found {len(errors)} errors.")

if __name__ == "__main__":
    validate_benchmark()
