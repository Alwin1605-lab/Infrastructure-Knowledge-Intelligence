import asyncio
import json
import os
import sys

# Ensure backend can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from motor.motor_asyncio import AsyncIOMotorClient
import chromadb
from neo4j import GraphDatabase
from app.config import get_settings

def resolve_host(uri: str, env_type: str) -> str:
    """Swap docker hostnames for localhost if running locally."""
    if env_type == "local":
        return uri.replace("mongodb:27017", "localhost:27017").replace("neo4j:7687", "localhost:7687").replace("chromadb:8000", "localhost:8000")
    return uri

async def main():
    print("Generating Live Corpus Snapshot...")
    settings = get_settings()
    
    # Determine execution environment via an env var or defaulting to local for dev scripts
    env_type = os.getenv("EXECUTION_ENV", "local")
    print(f"Execution Environment: {env_type}")
    
    # MongoDB
    mongo_uri = resolve_host(settings.MONGODB_URI, env_type)
    mongo_client = AsyncIOMotorClient(mongo_uri)
    db = mongo_client[settings.MONGODB_DATABASE]
    
    try:
        docs = await db.documents.find().to_list(1000)
        mongo_snapshot = [
            {
                'document_id': str(d.get('_id')),
                'filename': d.get('filename'),
                'status': d.get('processing_status')
            }
            for d in docs
        ]
    except Exception as e:
        print(f"MongoDB Error: {e}")
        mongo_snapshot = []
    
    # ChromaDB
    try:
        # Assuming script runs from root, path is ./chroma_db
        chroma_path = "./chroma_db"
        chroma_client = chromadb.PersistentClient(path=chroma_path)
        col = chroma_client.get_collection(settings.CHROMADB_COLLECTION)
        count = col.count()
        res = col.get(limit=10000, include=['metadatas'])
        chroma_docs = set([m.get('document_id') for m in res.get('metadatas', []) if m and 'document_id' in m])
        chroma_snapshot = {
            'collection_name': settings.CHROMADB_COLLECTION,
            'vector_count': count,
            'unique_document_ids': list(chroma_docs)
        }
    except Exception as e:
        print(f"ChromaDB Error: {e}")
        chroma_snapshot = {}
    
    # Neo4j
    neo4j_uri = resolve_host(settings.NEO4J_URI, env_type)
    try:
        neo4j_driver = GraphDatabase.driver(neo4j_uri, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD))
        with neo4j_driver.session() as session:
            entities = session.run('MATCH (n) RETURN count(n) as c').single()['c']
            relationships = session.run('MATCH ()-[r]->() RETURN count(r) as c').single()['c']
            source_docs = session.run('MATCH (n) WHERE n.source_document IS NOT NULL RETURN DISTINCT n.source_document as doc')
            source_docs_list = [record['doc'] for record in source_docs]
    except Exception as e:
        print(f"Neo4j Error: {e}")
        entities, relationships, source_docs_list = 0, 0, []
        
    neo4j_snapshot = {
        'entity_count': entities,
        'relationship_count': relationships,
        'source_documents': source_docs_list
    }
    
    snapshot = {
        'execution_environment': env_type,
        'mongodb': mongo_snapshot,
        'chromadb': chroma_snapshot,
        'neo4j': neo4j_snapshot
    }
    
    os.makedirs("experiments/v1", exist_ok=True)
    out_file = "experiments/v1/live_corpus_snapshot.json"
    with open(out_file, 'w', encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2)
        
    print(f"Snapshot saved to {out_file}")

if __name__ == "__main__":
    asyncio.run(main())
