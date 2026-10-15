import chromadb
import json

client = chromadb.PersistentClient(path='./chroma_db')
col = client.get_collection('infra_documents')
results = col.get()

samples = []
for i, (doc, meta) in enumerate(zip(results['documents'], results['metadatas'])):
    if len(doc) > 300 and "Table of Contents" not in doc and "..........." not in doc:
        samples.append({
            "chunk_id": results['ids'][i],
            "document": meta.get('filename', meta.get('document_id', 'unknown')),
            "page": meta.get('page_number', 1),
            "text": doc
        })
        if len(samples) >= 15:
            break

with open('chunk_samples.json', 'w', encoding='utf-8') as f:
    json.dump(samples, f, indent=2)
print("Saved meaningful chunk samples")
