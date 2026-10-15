import json

def expand_corpus():
    with open('knowledge_base_inventory.json', 'r', encoding='utf-8') as f:
        docs = json.load(f)
        
    # Sort docs by size or page count to prioritize small ones
    docs = sorted(docs, key=lambda x: x.get('page_count', 9999))
    
    selected_docs = []
    
    for doc in docs:
        if doc["filename"] == "DRCS Cover - To author.pdf":
            continue
            
        if doc.get("page_count", 9999) < 20 and doc.get("page_count", 0) > 0:
            selected_docs.append(doc["filename"])
            
        if len(selected_docs) >= 10:
            break
            
    print("Selected for ingestion:")
    for d in selected_docs:
        print(d)
        
if __name__ == "__main__":
    expand_corpus()
