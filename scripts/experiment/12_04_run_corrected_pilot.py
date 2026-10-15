import sys
import os
import json
import time
import asyncio
from datetime import datetime
import traceback
import importlib.util

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from app.rag.pipeline import HybridRAGPipeline
from app.agents.orchestrator import AgentOrchestrator
from app.rag.query_processor import QueryProcessor
from app.rag.context_fusion import ContextFuser
from app.llm import create_llm_provider
from app.embedding.huggingface import HuggingFaceEmbeddingService
from app.prompts.rag import RAGPrompts
from app.config import get_settings
from app.schemas.chat import ChatRequest
from app.knowledge_graph.queries import search_entities_by_text
from app.vectorstore.connection import init_vectorstore
from app.knowledge_graph.connection import init_kg

# Load experiment retriever
spec = importlib.util.spec_from_file_location("ExperimentRetriever", "scripts/12_experiment_retriever.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
ExperimentRetriever = module.ExperimentRetriever

async def run_corrected_pilot_async():
    print("PHASE 12.2 CORRECTED PILOT EXPERIMENT")
    
    with open("experiments/v2/corrected_benchmark_questions.json", "r", encoding="utf-8") as f:
        all_questions = json.load(f)
        
    questions = [q for q in all_questions if q.get("is_valid")]
    if len(questions) < 3:
        print("INSUFFICIENT_VALIDATED_QUESTIONS")
        return
        
    settings = get_settings()
    await init_vectorstore(settings)
    await init_kg(settings)
    
    llm = create_llm_provider(settings)
    embedder = HuggingFaceEmbeddingService(settings=settings)
    
    # Use ExperimentRetriever instead of ChromaRetriever to bypass metadata filter bug
    retriever = ExperimentRetriever(embedding_service=embedder, similarity_threshold=0.0)
    
    hybrid_pipeline = HybridRAGPipeline(llm_provider=llm, embedding_service=embedder, retriever=retriever)
    agent_orchestrator = AgentOrchestrator(llm_provider=llm, rag_pipeline=hybrid_pipeline)
    
    processor = QueryProcessor()
    fuser = ContextFuser()
    
    architectures = ["LLM-only", "RAG-only", "RAG+KG", "Hybrid RAG", "Hybrid RAG+Agentic"]
    
    results = []
    out_file = "experiments/v2/corrected_raw_results.json"
    
    for q in questions:
        q_id = q["question_id"]
        q_text = q["question"]
        
        for arch in architectures:
            print(f"Running {q_id} with {arch}...")
            
            run_result = {
                "run_id": f"{q_id}_{arch.replace(' ', '_').replace('+', '_')}_{int(time.time())}",
                "question_id": q_id,
                "architecture": arch,
                "timestamp": datetime.utcnow().isoformat(),
                "execution_type": "FAILED",
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
                "error": None
            }
            
            start_time = time.time()
            try:
                if arch == "LLM-only":
                    ans = await llm.generate(prompt=q_text, system_prompt="You are a helpful building engineering assistant.")
                    run_result["generated_answer"] = ans.content
                    run_result["status"] = "SUCCESS"
                    run_result["execution_type"] = "FULL_GENERATION"
                    
                elif arch == "RAG-only":
                    proc = processor.preprocess(q_text)
                    chunks = await retriever.retrieve(proc.expanded_query, top_k=5)
                    context = "\\n".join([c.text for c in chunks])
                    prompt = f"Context:\\n{context}\\n\\nQuestion: {q_text}"
                    ans = await llm.generate(prompt=prompt, system_prompt=RAGPrompts.SYSTEM_PROMPT)
                    
                    run_result["generated_answer"] = ans.content
                    run_result["retrieved_chunks"] = [{"id": c.document_id, "text": c.text, "document_name": c.document_name, "chunk_index": c.chunk_index} for c in chunks]
                    run_result["retrieved_documents"] = [c.document_name for c in chunks]
                    run_result["status"] = "SUCCESS"
                    run_result["execution_type"] = "FULL_GENERATION"
                    
                elif arch == "RAG+KG":
                    proc = processor.preprocess(q_text)
                    chunks = await retriever.retrieve(proc.expanded_query, top_k=5)
                    
                    sg = []
                    if proc.kg_search_terms:
                        ents = await search_entities_by_text(proc.kg_search_terms[0], limit=5)
                        if ents:
                            sg.append({"entities": ents, "relationships": []})
                            
                    from app.rag.reranker import RankedChunk
                    ranked_chunks = [RankedChunk(chunk=c, semantic_score=c.relevance_score, entity_boost=0.0, final_score=c.relevance_score, matched_entities=[]) for c in chunks]
                    fused = fuser.fuse(ranked_chunks, sg, q_text)
                    ans = await llm.generate(prompt=fused.full_prompt, system_prompt=RAGPrompts.SYSTEM_PROMPT)
                    
                    run_result["generated_answer"] = ans.content
                    run_result["retrieved_chunks"] = [{"id": c.document_id, "text": c.text, "document_name": c.document_name, "chunk_index": c.chunk_index} for c in chunks]
                    run_result["KG_entities"] = [e["id"] for s in sg for e in s["entities"]]
                    run_result["status"] = "SUCCESS"
                    run_result["execution_type"] = "FULL_GENERATION"
                    
                elif arch == "Hybrid RAG":
                    req = ChatRequest(question=q_text, top_k=5)
                    resp = await hybrid_pipeline.query(req)
                    
                    run_result["generated_answer"] = resp.answer
                    run_result["citations"] = [s.document_name for s in resp.sources]
                    run_result["retrieved_documents"] = [s.document_name for s in resp.sources]
                    run_result["confidence"] = resp.confidence.model_dump() if hasattr(resp.confidence, 'model_dump') else resp.confidence
                    if isinstance(resp.kg_context, list):
                        run_result["KG_entities"] = [e["id"] for s in resp.kg_context for e in s.get("entities", [])]
                    elif isinstance(resp.kg_context, dict):
                        run_result["KG_entities"] = resp.kg_context.get("entities", [])
                    
                    run_result["status"] = "SUCCESS"
                    run_result["execution_type"] = "EARLY_REJECTION" if run_result["confidence"].get("level") == "insufficient" else "FULL_GENERATION"
                    
                elif arch == "Hybrid RAG+Agentic":
                    resp = await agent_orchestrator.run(question=q_text, top_k=5)
                    run_result["generated_answer"] = resp.get("report", "")
                    rag_resp = resp.get("rag_response")
                    if rag_resp:
                        run_result["citations"] = [s.document_name for s in rag_resp.sources]
                        run_result["retrieved_documents"] = [s.document_name for s in rag_resp.sources]
                    else:
                        run_result["citations"] = []
                    run_result["confidence"] = resp.get("overall_confidence", 0.0)
                    run_result["agent_trace"] = resp.get("execution_trace", [])
                    
                    run_result["status"] = "SUCCESS"
                    run_result["execution_type"] = "FULL_GENERATION"
                    
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "rate" in err_str.lower():
                    run_result["status"] = "RATE_LIMITED"
                    run_result["execution_type"] = "RATE_LIMITED"
                elif "timeout" in err_str.lower():
                    run_result["status"] = "TIMEOUT"
                    run_result["execution_type"] = "TIMEOUT"
                else:
                    run_result["status"] = "FAILED"
                    run_result["execution_type"] = "FAILED"
                run_result["error"] = err_str
                traceback.print_exc()
                
            run_result["latency_ms"] = int((time.time() - start_time) * 1000)
            results.append(run_result)
            
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)
                
            await asyncio.sleep(2)
            
    print("\\nCorrected Pilot Complete!")

if __name__ == "__main__":
    asyncio.run(run_corrected_pilot_async())
