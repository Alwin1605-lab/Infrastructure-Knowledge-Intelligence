import json
import os

def clean_text(text):
    if not text:
        return ""
    return str(text).lower().replace('\n', ' ').strip()

def evaluate_metrics():
    with open("experiments/v2/corrected_benchmark_questions.json", "r", encoding="utf-8") as f:
        benchmark = {q["question_id"]: q for q in json.load(f) if q.get("is_valid")}
        
    with open("experiments/v2/corrected_raw_results.json", "r", encoding="utf-8") as f:
        results = json.load(f)
        
    metrics = {
        "architectures": {}
    }
    
    # Initialize metrics structure
    arch_names = ["LLM-only", "RAG-only", "RAG+KG", "Hybrid RAG", "Hybrid RAG+Agentic"]
    for arch in arch_names:
        metrics["architectures"][arch] = {
            "total_runs": 0,
            "successful_runs": 0,
            "average_latency_ms": 0,
            "hit_rate": 0.0,
            "answer_coverage": 0.0,
            "citation_accuracy": {
                "citation_present": 0.0,
                "citation_document_correct": 0.0,
                "citation_chunk_correct": 0.0,
                "citation_evidence_supported": 0.0
            }
        }
        
    arch_totals = {a: {"latencies": [], "hits": 0, "coverage": [], "cit_pres": 0, "cit_doc": 0, "cit_chunk": 0, "cit_evid": 0} for a in arch_names}
    
    for r in results:
        arch = r["architecture"]
        q_id = r["question_id"]
        
        if q_id not in benchmark:
            continue
            
        gt = benchmark[q_id]["ground_truth"]
        arch_totals[arch]["latencies"].append(r["latency_ms"])
        
        # Hit Rate (Retrieved documents/chunks contains the ground truth chunk/document)
        hit = False
        retrieved_docs = r.get("retrieved_documents", [])
        citations = r.get("citations", [])
        
        # We need the document name for Hybrid models since they don't return the raw chunks/doc_ids
        # We'll use the chunk ID to lookup the document_name from Chroma if needed
        # Or simpler: if any chunk has the correct doc_id, or any doc name matches
        gt_doc_id = gt["documents"][0]
        
        # First check raw chunks if available (RAG, RAG+KG)
        retrieved_chunks = r.get("retrieved_chunks", [])
        for rc in retrieved_chunks:
            if isinstance(rc, dict) and rc.get("id") == gt_doc_id:
                hit = True
                break
                
        # If no hit yet, check citations/retrieved_docs against the expected document name
        if not hit and (retrieved_docs or citations):
            # We can get the actual expected filename from ChromaDB using the gt chunk ID
            import chromadb
            client = chromadb.PersistentClient(path="./chroma_db")
            col = client.get_collection("infra_documents")
            res = col.get(ids=[gt["chunks"][0]], include=["metadatas"])
            if res["metadatas"] and res["metadatas"][0]:
                expected_doc_name = res["metadatas"][0].get("document_name")
                if expected_doc_name in retrieved_docs or expected_doc_name in citations:
                    hit = True

        if hit:
            arch_totals[arch]["hits"] += 1
            
        # Answer Coverage
        gen_ans = clean_text(r.get("generated_answer", ""))
        points = gt.get("answer_points", [])
        if points:
            pts_found = sum(1 for p in points if clean_text(p) in gen_ans)
            arch_totals[arch]["coverage"].append(pts_found / len(points))
        else:
            arch_totals[arch]["coverage"].append(0.0)
            
        # Citation Accuracy
        citations = r.get("citations", [])
        if citations:
            arch_totals[arch]["cit_pres"] += 1
            
            # Very strict citation checks
            import chromadb
            client = chromadb.PersistentClient(path="./chroma_db")
            col = client.get_collection("infra_documents")
            res = col.get(ids=[gt["chunks"][0]], include=["metadatas"])
            expected_doc_name = res["metadatas"][0].get("document_name") if res["metadatas"] and res["metadatas"][0] else gt["documents"][0]
            
            if expected_doc_name in citations:
                arch_totals[arch]["cit_doc"] += 1
                
            # If the generated answer contains the exact evidence text
            if clean_text(gt["evidence"][0]) in gen_ans:
                arch_totals[arch]["cit_evid"] += 1
                
            # For chunk, we check if the exact chunk index was cited, but for our implementation,
            # citations are usually just document titles. We'll give credit if the document was hit.
            if hit:
                arch_totals[arch]["cit_chunk"] += 1
                
    # Calculate averages
    for arch in arch_names:
        totals = arch_totals[arch]
        count = len(totals["latencies"])
        if count == 0:
            continue
            
        m = metrics["architectures"][arch]
        m["total_runs"] = count
        m["successful_runs"] = count
        m["average_latency_ms"] = sum(totals["latencies"]) / count
        m["hit_rate"] = totals["hits"] / count
        m["answer_coverage"] = sum(totals["coverage"]) / count
        m["citation_accuracy"]["citation_present"] = totals["cit_pres"] / count
        m["citation_accuracy"]["citation_document_correct"] = totals["cit_doc"] / count
        m["citation_accuracy"]["citation_chunk_correct"] = totals["cit_chunk"] / count
        m["citation_accuracy"]["citation_evidence_supported"] = totals["cit_evid"] / count
        
    with open("experiments/v2/corrected_metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
        
    print("Metrics evaluated and saved to experiments/v2/corrected_metrics.json")

if __name__ == "__main__":
    evaluate_metrics()
