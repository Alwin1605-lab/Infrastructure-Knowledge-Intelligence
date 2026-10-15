import json
import asyncio
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from app.config import get_settings
from app.embedding.huggingface import HuggingFaceEmbeddingService
from app.vectorstore.connection import init_vectorstore
from app.vectorstore.retriever import ChromaRetriever
import importlib.util
spec = importlib.util.spec_from_file_location("ExperimentRetriever", "scripts/12_experiment_retriever.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
ExperimentRetriever = module.ExperimentRetriever

async def main():
    print("Running Retrieval Diagnostics...")
    settings = get_settings()
    
    await init_vectorstore(settings)
    e_service = HuggingFaceEmbeddingService(settings)
    
    prod_retriever = ChromaRetriever(e_service, similarity_threshold=0.0)
    exp_retriever = ExperimentRetriever(e_service, similarity_threshold=0.0)
    
    with open("experiments/v2/corrected_benchmark_questions.json", "r", encoding="utf-8") as f:
        questions = json.load(f)
        
    report_lines = ["# Phase 12.2 Retrieval Diagnostic Report\n"]
    
    for q in questions:
        if not q.get("is_valid"):
            continue
            
        q_id = q["question_id"]
        q_text = q["question"]
        
        report_lines.append(f"## {q_id}\n")
        report_lines.append(f"**Query**: {q_text}\n")
        report_lines.append(f"**Embedding Dimension**: 384 (all-MiniLM-L6-v2)\n")
        report_lines.append(f"**Collection**: {settings.CHROMADB_COLLECTION}\n")
        report_lines.append(f"**Top K**: 5\n\n")
        
        # Test Production
        prod_chunks = await prod_retriever.retrieve(q_text, top_k=5)
        report_lines.append("### PRODUCTION RETRIEVER\n")
        report_lines.append(f"- **Returned Chunks**: {len(prod_chunks)}\n")
        if prod_chunks:
            report_lines.append("- **Document IDs**: " + ", ".join([c.document_id for c in prod_chunks]) + "\n")
            report_lines.append("- **Chunk Indices**: " + ", ".join([str(c.chunk_index) for c in prod_chunks]) + "\n")
            report_lines.append("- **Similarity Scores**: " + ", ".join([str(c.relevance_score) for c in prod_chunks]) + "\n")
        else:
            report_lines.append("- *No chunks retrieved due to is_global metadata filter mismatch.*\n")
        report_lines.append("\n")
        
        # Test Experiment
        exp_chunks = await exp_retriever.retrieve(q_text, top_k=5)
        report_lines.append("### EXPERIMENT RETRIEVER\n")
        report_lines.append(f"- **Returned Chunks**: {len(exp_chunks)}\n")
        if exp_chunks:
            report_lines.append("- **Document IDs**: " + ", ".join([c.document_id for c in exp_chunks]) + "\n")
            report_lines.append("- **Chunk Indices**: " + ", ".join([str(c.chunk_index) for c in exp_chunks]) + "\n")
            report_lines.append("- **Similarity Scores**: " + ", ".join([str(c.relevance_score) for c in exp_chunks]) + "\n")
        report_lines.append("\n---\n")

    with open("experiments/v2/retrieval_diagnostic.md", "w", encoding="utf-8") as f:
        f.writelines(report_lines)
        
    print("Retrieval diagnostic saved to experiments/v2/retrieval_diagnostic.md")

if __name__ == "__main__":
    asyncio.run(main())
