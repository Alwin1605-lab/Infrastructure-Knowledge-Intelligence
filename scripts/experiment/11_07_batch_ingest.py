import subprocess

with open('docs_to_ingest.txt', 'r', encoding='utf-16') as f:
    lines = f.readlines()
    
for line in lines[1:]: # Skip "Selected for ingestion:"
    doc = line.strip()
    if not doc: continue
    print(f"Ingesting {doc}...")
    subprocess.run(["python", "03_ingest_knowledge_base.py", "--document", doc])
    
print("All ingestion commands finished.")
