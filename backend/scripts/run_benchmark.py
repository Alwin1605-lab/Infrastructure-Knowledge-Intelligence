import asyncio
import os
import sys
import json
import time
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.config import get_settings
from app.agents.query_analysis_agent import QueryAnalysisAgent
from app.models.document import Document
from app.services.rag_service import RAGService
from app.services.rag_service import RAGService

async def run_benchmark():
    settings = get_settings()
    
    # Init MongoDB
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    await init_beanie(database=client[settings.MONGODB_DATABASE], document_models=[Document])
    
    # Init Services
    rag = RAGService()
    query_agent = QueryAnalysisAgent(settings.LLM_PROVIDER)
    
    with open(os.path.join(os.path.dirname(__file__), "benchmark_questions.json"), "r") as f:
        questions = json.load(f)
        
    print(f"Starting Benchmark against {len(questions)} questions...\n")
    
    results = []
    category_metrics = {}
    
    for q in questions:
        print(f"Testing [{q['category']}]: {q['question']}")
        
        start_time = time.time()
        try:
            # 1. Analyze
            analysis = await query_agent.analyze(q['question'])
            
            # 2. Retrieve
            vector_results = await rag.search(q['question'], k=3)
            
            # 3. We'll simulate a quick heuristic evaluation since running full LLM generation
            # takes time and costs tokens. In a real system, we would run the full generation pipeline.
            # Here we check if expected keywords are present in retrieved contexts.
            
            retrieved_text = " ".join([c['content'] for c in vector_results])
            retrieved_text = retrieved_text.lower()
            
            keywords_found = [kw for kw in q['expected_keywords'] if kw.lower() in retrieved_text]
            accuracy = len(keywords_found) / len(q['expected_keywords']) * 100
            
            latency = time.time() - start_time
            
            result = {
                "id": q['id'],
                "category": q['category'],
                "latency_s": latency,
                "accuracy": accuracy,
                "keywords_found": keywords_found,
                "citations": len(vector_results)
            }
            results.append(result)
            
            if q['category'] not in category_metrics:
                category_metrics[q['category']] = {"acc": [], "lat": []}
            category_metrics[q['category']]["acc"].append(accuracy)
            category_metrics[q['category']]["lat"].append(latency)
            
            print(f"  -> Accuracy: {accuracy:.1f}% | Latency: {latency:.2f}s | Citations: {len(vector_results)}")
            
        except Exception as e:
            print(f"  -> Failed: {e}")
            
    # Generate summary
    print("\nGenerating Benchmark Reports...")
    
    overall_acc = sum(r['accuracy'] for r in results) / len(results) if results else 0
    overall_lat = sum(r['latency_s'] for r in results) / len(results) if results else 0
    
    summary_md = f"""# Knowledge Base Benchmark Summary

## Overall Performance
- **Average Retrieval Accuracy**: {overall_acc:.1f}%
- **Average Response Latency**: {overall_lat:.2f}s
- **Total Questions Evaluated**: {len(results)}

## Performance by Category
"""
    for cat, metrics in category_metrics.items():
        cat_acc = sum(metrics['acc']) / len(metrics['acc'])
        cat_lat = sum(metrics['lat']) / len(metrics['lat'])
        summary_md += f"- **{cat}**: {cat_acc:.1f}% accuracy | {cat_lat:.2f}s latency\n"
        
    summary_md += "\n## Detailed Results\n"
    for r in results:
        summary_md += f"- **Q{r['id']}** ({r['category']}): {r['accuracy']:.1f}% (Found: {', '.join(r['keywords_found'])})\n"
        
    with open("benchmark_summary.md", "w") as f:
        f.write(summary_md)
        
    with open("benchmark_results.json", "w") as f:
        json.dump({
            "overall_accuracy": overall_acc,
            "overall_latency": overall_lat,
            "results": results
        }, f, indent=2)
        
    print("Generated benchmark_summary.md and benchmark_results.json")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
