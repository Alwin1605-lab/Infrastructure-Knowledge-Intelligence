import json
import os
import glob
import re

def clean_text(text):
    if not text:
        return ""
    return re.sub(r'\s+', ' ', str(text).lower().strip())

def calculate_metrics():
    print("Calculating Phase 12 Metrics...")
    
    with open("benchmark_questions.json", "r", encoding="utf-8") as f:
        benchmark = json.load(f)
        
    benchmark_map = {q["id"]: q for q in benchmark}
    
    # Find latest raw results
    raw_files = sorted(glob.glob("experiments/v1/experiment_raw_results_v*.json"))
    if not raw_files:
        print("No raw results found!")
        return
        
    latest_file = raw_files[-1]
    print(f"Reading from {latest_file}")
    
    with open(latest_file, "r", encoding="utf-8") as f:
        raw_results = json.load(f)
        
    # Initialize metrics structure
    architectures = ["LLM-only", "RAG-only", "RAG+KG", "Hybrid RAG", "Hybrid RAG+Agentic"]
    summary = {
        "metadata": {
            "total_questions": len(benchmark),
            "total_architectures": len(architectures),
            "total_expected_runs": len(benchmark) * len(architectures),
            "actual_successful_runs": 0,
            "failed_runs": 0,
            "timeout_runs": 0,
            "rate_limited_runs": 0
        },
        "architectures": {}
    }
    
    for arch in architectures:
        summary["architectures"][arch] = {
            "runs": 0,
            "success_rate": 0.0,
            "latency": {"mean": "NOT_VERIFIABLE", "median": "NOT_VERIFIABLE", "min": "NOT_VERIFIABLE", "max": "NOT_VERIFIABLE", "p95": "NOT_STATISTICALLY_MEANINGFUL"},
            "retrieval": {"hit_rate": "NOT_VERIFIABLE", "precision": "NOT_VERIFIABLE", "recall": "NOT_VERIFIABLE", "mrr": "NOT_VERIFIABLE"},
            "answer": {"point_coverage": "NOT_VERIFIABLE", "citation_coverage": "NOT_VERIFIABLE", "semantic_quality": "NOT_EVALUATED"},
            "kg": {"entity_coverage": "NOT_APPLICABLE", "relationship_coverage": "NOT_APPLICABLE"},
            "agent": {"success_rate": "NOT_APPLICABLE"}
        }
        
    arch_data = {arch: [] for arch in architectures}
    
    for row in raw_results:
        arch = row["architecture"]
        status = row["status"]
        
        if status == "SUCCESS":
            summary["metadata"]["actual_successful_runs"] += 1
        elif status == "FAILED":
            summary["metadata"]["failed_runs"] += 1
        elif status == "TIMEOUT":
            summary["metadata"]["timeout_runs"] += 1
        elif status == "RATE_LIMITED":
            summary["metadata"]["rate_limited_runs"] += 1
            
        arch_data[arch].append(row)
        
    for arch in architectures:
        runs = arch_data[arch]
        valid_runs = [r for r in runs if r["status"] == "SUCCESS"]
        
        num_runs = len(runs)
        num_valid = len(valid_runs)
        
        if num_runs > 0:
            summary["architectures"][arch]["success_rate"] = num_valid / num_runs
            
        if num_valid == 0:
            continue
            
        # Latency
        latencies = sorted([r["latency_ms"] for r in valid_runs])
        summary["architectures"][arch]["latency"] = {
            "mean": round(sum(latencies) / num_valid, 2),
            "median": latencies[num_valid // 2],
            "min": latencies[0],
            "max": latencies[-1],
            "p95": "NOT_STATISTICALLY_MEANINGFUL"
        }
        
        # Retrieval Metrics (only if retrieval is expected)
        if arch != "LLM-only":
            hits = 0
            precisions = []
            recalls = []
            mrrs = []
            
            for r in valid_runs:
                q_id = r["question_id"]
                gt = benchmark_map[q_id]
                gt_text = clean_text(gt["ground_truth_evidence"])
                
                retrieved = r.get("retrieved_chunks", [])
                
                # Check each chunk
                is_hit = False
                rank = -1
                rel_count = 0
                for i, chunk in enumerate(retrieved):
                    c_text = clean_text(chunk)
                    if gt_text and (gt_text in c_text or c_text in gt_text):
                        is_hit = True
                        rel_count += 1
                        if rank == -1:
                            rank = i + 1
                            
                if is_hit:
                    hits += 1
                    mrrs.append(1.0 / rank)
                else:
                    mrrs.append(0.0)
                    
                precisions.append(rel_count / max(len(retrieved), 1))
                recalls.append(1.0 if is_hit else 0.0)
                
            summary["architectures"][arch]["retrieval"] = {
                "hit_rate": round(hits / num_valid, 2),
                "precision": round(sum(precisions) / num_valid, 2),
                "recall": round(sum(recalls) / num_valid, 2),
                "mrr": round(sum(mrrs) / num_valid, 2)
            }
            
        # Answer metrics
        pts_coverage = []
        cit_coverage = []
        
        for r in valid_runs:
            q_id = r["question_id"]
            gt = benchmark_map[q_id]
            ans_text = clean_text(r["generated_answer"])
            
            # Points
            pts = gt.get("expected_answer_points", [])
            covered_pts = 0
            for pt in pts:
                if clean_text(pt) in ans_text:
                    covered_pts += 1
            if pts:
                pts_coverage.append(covered_pts / len(pts))
                
            # Citations
            cits = gt.get("source_document", "")
            ans_cits = " ".join([clean_text(c) for c in r.get("citations", [])])
            if clean_text(cits) in ans_text or clean_text(cits) in ans_cits:
                cit_coverage.append(1.0)
            else:
                cit_coverage.append(0.0)
                
        summary["architectures"][arch]["answer"]["point_coverage"] = round(sum(pts_coverage) / max(len(pts_coverage), 1), 2)
        summary["architectures"][arch]["answer"]["citation_coverage"] = round(sum(cit_coverage) / max(len(cit_coverage), 1), 2)
        
        # KG metrics
        if "KG" in arch or "Agentic" in arch:
            # We don't have exact ground truth for KG entities yet in benchmark_questions.json,
            # so we check if ANY entities were returned.
            ent_cov = []
            for r in valid_runs:
                ents = r.get("KG_entities", [])
                ent_cov.append(1.0 if len(ents) > 0 else 0.0)
            
            summary["architectures"][arch]["kg"] = {
                "entity_coverage": round(sum(ent_cov) / max(len(ent_cov), 1), 2),
                "relationship_coverage": "NOT_VERIFIABLE"
            }
            
        # Agent metrics
        if "Agentic" in arch:
            summary["architectures"][arch]["agent"] = {
                "success_rate": summary["architectures"][arch]["success_rate"]
            }

    # Auto-version output
    out_file = "experiments/v1/experiment_summary_v1.json"
    version = 1
    while os.path.exists(out_file):
        version += 1
        out_file = f"experiments/v1/experiment_summary_v{version}.json"
        
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
        
    print(f"Metrics saved to: {out_file}")

if __name__ == "__main__":
    calculate_metrics()
