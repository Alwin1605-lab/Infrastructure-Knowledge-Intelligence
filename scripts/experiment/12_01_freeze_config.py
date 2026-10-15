import json
import os
import sys
import hashlib
from datetime import datetime

def get_file_hash(filepath):
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        # Load and dump to normalize JSON formatting before hashing
        data = json.load(f)
        normalized = json.dumps(data, sort_keys=True)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

def freeze_config():
    print("Freezing Phase 12 Experiment Configuration...")
    
    os.makedirs("experiments/v1", exist_ok=True)
    
    corpus_hash = get_file_hash("research_corpus.json")
    benchmark_hash = get_file_hash("benchmark_questions.json")
    
    if not corpus_hash or not benchmark_hash:
        print("ERROR: Missing corpus or benchmark files.")
        return
        
    config = {
        "timestamp": datetime.utcnow().isoformat(),
        "environment": {
            "os": sys.platform,
            "python_version": sys.version.split()[0],
        },
        "hashes": {
            "corpus_hash": corpus_hash,
            "benchmark_hash": benchmark_hash
        },
        "models": {
            "llm_model": "llama-3.1-8b-instant",
            "embedding_model": "all-MiniLM-L6-v2"
        },
        "chunking": {
            "chunk_size": 1000,
            "chunk_overlap": 200
        },
        "knowledge_graph": {
            "batch_size": 5
        }
    }
    
    config_hash = hashlib.sha256(json.dumps(config, sort_keys=True).encode("utf-8")).hexdigest()
    config["hashes"]["configuration_hash"] = config_hash
    
    with open("experiments/v1/experiment_config_v1.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
        
    print(f"Frozen configuration saved. Config Hash: {config_hash}")

if __name__ == "__main__":
    freeze_config()
