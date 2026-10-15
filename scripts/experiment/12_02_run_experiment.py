import sys
import os
import json
import time
import asyncio
from datetime import datetime
import traceback

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from app.rag.pipeline import HybridRAGPipeline
from app.agents.orchestrator import AgentOrchestrator
from app.rag.query_processor import QueryProcessor
from app.vectorstore.retriever import ChromaRetriever
from app.rag.context_fusion import ContextFuser
from app.llm import create_llm_provider
from app.embedding.huggingface import HuggingFaceEmbeddingService
from app.prompts.rag import RAGPrompts
from app.config import get_settings
from app.schemas.chat import ChatRequest
from app.knowledge_graph.queries import search_entities_by_text
from app.vectorstore.connection import init_vectorstore

from app.knowledge_graph.connection import init_kg

async def run_experiment_async():
    print("PHASE 12 PILOT EXPERIMENT")
    
    config_file = "experiments/v1/experiment_config_v1.json"
    if not os.path.exists(config_file):
        print("Run 12_01_freeze_config.py first!")
        return
        
    with open("benchmark_questions.json", "r", encoding="utf-8") as f:
        questions = json.load(f)
        
    settings = get_settings()
    await init_vectorstore(settings)
    await init_kg(settings)
    
    llm = create_llm_provider(settings)
    embedder = HuggingFaceEmbeddingService(settings=settings)
    
    retriever = ChromaRetriever(embedding_service=embedder)
    hybrid_pipeline = HybridRAGPipeline(llm_provider=llm, embedding_service=embedder, retriever=retriever)
    agent_orchestrator = AgentOrchestrator(llm_provider=llm, rag_pipeline=hybrid_pipeline)
    
    processor = QueryProcessor()
    fuser = ContextFuser()
    
    results = []
    
    architectures = [
        "LLM-only",
        "RAG-only",
        "RAG+KG",
        "Hybrid RAG",
        "Hybrid RAG+Agentic"
    ]
    
    stats = {
        "Successful": 0,
        "Failed": 0,
        "Timeout": 0,
        "Rate Limited": 0
    }
    
    out_file = "experiments/v1/experiment_raw_results_v1.json"
    version = 1
    while os.path.exists(out_file):
        version += 1
        out_file = f"experiments/v1/experiment_raw_results_v{version}.json"
        
    print(f"Output will be saved to: {out_file}")
    
    for q_idx, q in enumerate(questions):
        q_id = q["id"]
        q_text = q["question"]
        
        for arch in architectures:
            print(f"Running Q{q_id} with {arch}...")
            
            run_result = {
                "run_id": f"{q_id}_{arch.replace(' ', '_').replace('+', '_')}_{int(time.time())}",
                "question_id": q_id,
                "architecture": arch,
                "timestamp": datetime.utcnow().isoformat(),
                "latency_ms": 0,
                "status": "FAILED",
                "generated_answer": None,
                "retrieved_documents": [],
                "retrieved_chunks": [],
                "citations": [],
                "confidence": None,
                "KG_entities": [],
                "KG_relationships": [],
                "agent_trace": None,
                "error": None,
                "error_type": None
            }
            
            start_time = time.time()
            try:
                if arch == "LLM-only":
                    ans = await llm.generate(prompt=q_text, system_prompt="You are a helpful building engineering assistant.")
                    run_result["generated_answer"] = ans.content
                    run_result["status"] = "SUCCESS"
                    
                elif arch == "RAG-only":
                    proc = processor.preprocess(q_text)
                    chunks = await retriever.retrieve(proc.expanded_query, top_k=5)
                    
                    context = "\\n".join([c.text for c in chunks])
                    prompt = f"Context:\\n{context}\\n\\nQuestion: {q_text}"
                    ans = await llm.generate(prompt=prompt, system_prompt=RAGPrompts.SYSTEM_PROMPT)
                    
                    run_result["generated_answer"] = ans.content
                    run_result["retrieved_chunks"] = [c.text for c in chunks]
                    run_result["retrieved_documents"] = [c.metadata.get("filename", "") for c in chunks]
                    run_result["status"] = "SUCCESS"
                    
                elif arch == "RAG+KG":
                    proc = processor.preprocess(q_text)
                    chunks = await retriever.retrieve(proc.expanded_query, top_k=5)
                    
                    sg = []
                    if proc.kg_search_terms:
                        ents = await search_entities_by_text(proc.kg_search_terms[0], limit=5)
                        if ents:
                            sg.append({"entities": ents, "relationships": []})
                            
                    fused = fuser.fuse(chunks, sg, q_text)
                    ans = await llm.generate(prompt=fused.full_prompt, system_prompt=RAGPrompts.SYSTEM_PROMPT)
                    
                    run_result["generated_answer"] = ans.content
                    run_result["retrieved_chunks"] = [c.text for c in chunks]
                    run_result["KG_entities"] = [e["id"] for s in sg for e in s["entities"]]
                    run_result["status"] = "SUCCESS"
                    
                elif arch == "Hybrid RAG":
                    req = ChatRequest(question=q_text, top_k=5)
                    resp = await hybrid_pipeline.query(req)
                    
                    run_result["generated_answer"] = resp.answer
                    run_result["citations"] = [s.document_title for s in resp.sources]
                    run_result["retrieved_documents"] = [s.document_title for s in resp.sources]
                    run_result["confidence"] = resp.confidence.model_dump() if hasattr(resp.confidence, 'model_dump') else resp.confidence
                    if isinstance(resp.kg_context, list):
                        run_result["KG_entities"] = [e["id"] for s in resp.kg_context for e in s.get("entities", [])]
                    elif isinstance(resp.kg_context, dict):
                        run_result["KG_entities"] = resp.kg_context.get("entities", [])
                    run_result["status"] = "SUCCESS"
                    
                elif arch == "Hybrid RAG+Agentic":
                    resp = await agent_orchestrator.run(question=q_text, top_k=5)
                    
                    run_result["generated_answer"] = resp.get("answer", "")
                    run_result["citations"] = [s.get("document_title", "") for s in resp.get("sources", [])]
                    run_result["confidence"] = resp.get("confidence", {})
                    
                    kg_ctx = resp.get("kg_context", [])
                    if isinstance(kg_ctx, list):
                        run_result["KG_entities"] = [e["id"] for s in kg_ctx for e in s.get("entities", [])]
                    elif isinstance(kg_ctx, dict):
                        run_result["KG_entities"] = kg_ctx.get("entities", [])
                        
                    run_result["agent_trace"] = resp.get("agent_trace", [])
                    run_result["status"] = "SUCCESS"
                    
                stats["Successful"] += 1
                
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "rate" in err_str.lower():
                    run_result["status"] = "RATE_LIMITED"
                    stats["Rate Limited"] += 1
                elif "timeout" in err_str.lower():
                    run_result["status"] = "TIMEOUT"
                    stats["Timeout"] += 1
                else:
                    run_result["status"] = "FAILED"
                    stats["Failed"] += 1
                    
                run_result["error"] = err_str
                run_result["error_type"] = e.__class__.__name__
                traceback.print_exc()
                
            run_result["latency_ms"] = int((time.time() - start_time) * 1000)
            results.append(run_result)
            
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)
                
            await asyncio.sleep(2)
            
    print("\\nExperiment Complete!")
    for k, v in stats.items():
        print(f"{k}: {v}")

def run_experiment():
    asyncio.run(run_experiment_async())

if __name__ == "__main__":
    run_experiment()
