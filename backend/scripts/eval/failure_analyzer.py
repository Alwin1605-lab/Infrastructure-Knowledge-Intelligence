import json
import os

def analyze_failures(results_path: str):
    if not os.path.exists(results_path):
        print("No benchmark results found.")
        return
        
    with open(results_path, "r") as f:
        data = json.load(f)
        
    failures = []
    classifications = {
        "Poor Retrieval": 0,
        "Missing Knowledge": 0,
        "Hallucination Risk": 0,
        "Low Confidence": 0,
        "Missing Knowledge Graph Links": 0
    }
    
    for r in data["results"]:
        metrics = r["metrics"]
        trace = r["trace"]
        
        reasons = []
        if metrics["retrieval_hit_rate"] == 0:
            reasons.append("Missing Knowledge")
            classifications["Missing Knowledge"] += 1
        elif metrics["retrieval_precision"] < 0.5:
            reasons.append("Poor Retrieval")
            classifications["Poor Retrieval"] += 1
            
        if metrics["kg_coverage"] < 0.5:
            reasons.append("Missing Knowledge Graph Links")
            classifications["Missing Knowledge Graph Links"] += 1
            
        if metrics["confidence"] < 0.7 and metrics["retrieval_hit_rate"] > 0:
            reasons.append("Low Confidence")
            classifications["Low Confidence"] += 1
            
        if len(reasons) > 0:
            failures.append({
                "id": r["id"],
                "question": r["question"],
                "reasons": reasons,
                "missing_entities": trace["missing_entities"]
            })
            
    analysis_report = {
        "total_failures_detected": len(failures),
        "failure_classifications": classifications,
        "detailed_failures": failures
    }
    
    out_path = os.path.join(os.path.dirname(results_path), "failure_analysis.json")
    with open(out_path, "w") as f:
        json.dump(analysis_report, f, indent=2)
        
    print("\n=== Failure Analysis Report ===")
    print(f"Total Failures: {len(failures)}")
    for k, v in classifications.items():
        print(f"  - {k}: {v}")
        
    return analysis_report

if __name__ == "__main__":
    base_dir = os.path.dirname(__file__)
    analyze_failures(os.path.join(base_dir, "benchmark_results.json"))
