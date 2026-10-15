import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

import asyncio
import json
from app.config import get_settings
from app.vectorstore.connection import init_vectorstore
from app.vectorstore.retriever import ChromaRetriever
import importlib.util

spec = importlib.util.spec_from_file_location("experiment_retriever", "scripts/12_experiment_retriever.py")
expr_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(expr_module)
ExperimentRetriever = expr_module.ExperimentRetriever

async def verify_retrieval():
    settings = get_settings()
    await init_vectorstore(settings)
    
    # We must instantiate the proper dependencies
    from app.embedding.huggingface import HuggingFaceEmbeddingService
    embedding_service = HuggingFaceEmbeddingService(settings)
    
    prod_retriever = ChromaRetriever(embedding_service=embedding_service)
    exp_retriever = ExperimentRetriever(embedding_service=embedding_service)
    
    with open("experiments/v2/corrected_benchmark_questions.json", "r") as f:
        questions = json.load(f)
        
    results_md = "# Production Retrieval Verification\n\n"
    
    for q_data in questions:
        q_id = q_data["question_id"]
        query = q_data["question"]
        
        # We simulate the exact way Phase 12 queried it: top_k=5
        # The prod retriever uses workspace_id=None (default, which implies Global)
        prod_chunks = await prod_retriever.retrieve(query, top_k=5)
        exp_chunks = await exp_retriever.retrieve(query, top_k=5)
        
        prod_ids = [f"{c.document_id}_{c.chunk_index}" for c in prod_chunks]
        exp_ids = [f"{c.document_id}_{c.chunk_index}" for c in exp_chunks]
        
        # Compare
        match_count = len(set(prod_ids) & set(exp_ids))
        
        results_md += f"## Question: {q_id}\n"
        results_md += f"**Query**: {query}\n\n"
        results_md += f"- **Production Chunks**: {len(prod_chunks)}\n"
        results_md += f"- **Experiment Chunks**: {len(exp_chunks)}\n"
        results_md += f"- **Matching Chunk IDs**: {match_count} / {max(len(prod_chunks), len(exp_chunks))}\n\n"
        
        results_md += "### Production Results\n"
        for i, c in enumerate(prod_chunks):
            results_md += f"{i+1}. `{c.document_id}_{c.chunk_index}` (Doc: {c.document_id}) - Score: {c.relevance_score:.4f}\n"
            
        results_md += "\n### Experiment Results\n"
        for i, c in enumerate(exp_chunks):
            results_md += f"{i+1}. `{c.document_id}_{c.chunk_index}` (Doc: {c.document_id}) - Score: {c.relevance_score:.4f}\n"
            
        results_md += "\n---\n"
        
    with open("experiments/v2/production_retrieval_verification.md", "w", encoding="utf-8") as f:
        f.write(results_md)
        
    print("Verification complete! Saved to experiments/v2/production_retrieval_verification.md")
    
if __name__ == "__main__":
    asyncio.run(verify_retrieval())
