import json
import os
from collections import defaultdict

def curate_corpus():
    print("Curating final research corpus...")
    
    # Load completed documents
    if not os.path.exists("research_corpus_inventory.json"):
        print("Missing research_corpus_inventory.json. Run 11_01 first.")
        return
        
    with open("research_corpus_inventory.json", "r", encoding="utf-8") as f:
        completed_docs = json.load(f)
        
    # Load ALL documents to find excluded ones
    if not os.path.exists("knowledge_base_inventory.json"):
        print("Missing knowledge_base_inventory.json.")
        return
        
    with open("knowledge_base_inventory.json", "r", encoding="utf-8") as f:
        all_docs = json.load(f)
        
    completed_filenames = {doc["filename"]: doc for doc in completed_docs}
    
    selected = []
    excluded = []
    category_counts = defaultdict(int)
    
    for doc in all_docs:
        filename = doc["filename"]
        if filename in completed_filenames:
            selected.append(completed_filenames[filename])
            category_counts[completed_filenames[filename]["category"]] += 1
        else:
            excluded.append({
                "filename": filename,
                "reason": "Not successfully processed / Not indexed"
            })
            
    corpus_data = {
        "summary": {
            "total_selected": len(selected),
            "total_excluded": len(excluded),
            "category_distribution": dict(category_counts)
        },
        "selected_documents": selected,
        "excluded_documents": excluded
    }
    
    with open("research_corpus.json", "w", encoding="utf-8") as f:
        json.dump(corpus_data, f, indent=2)
        
    print(f"Curated {len(selected)} documents into research_corpus.json.")
    if len(selected) < 10:
        print("WARNING: FRAMEWORK_VALIDATION_ONLY. Corpus is too small for a full research experiment.")

if __name__ == "__main__":
    curate_corpus()
