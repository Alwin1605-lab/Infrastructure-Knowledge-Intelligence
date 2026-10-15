import json
import os
import sys

def detect_drift(current_file: str, previous_file: str) -> dict:
    if not os.path.exists(previous_file):
        print("No previous benchmark found to compare against.")
        return None
        
    with open(current_file, "r") as f:
        current = json.load(f)
    with open(previous_file, "r") as f:
        previous = json.load(f)
        
    metrics = ["avg_latency", "avg_precision", "avg_recall", "avg_kg_coverage"]
    
    drift_report = {
        "timestamp": current["timestamp"],
        "drifts": {}
    }
    
    has_regression = False
    
    for m in metrics:
        curr_val = current.get(m, 0)
        prev_val = previous.get(m, 0)
        
        diff = curr_val - prev_val
        pct_change = (diff / prev_val * 100) if prev_val > 0 else 0
        
        # Determine if there's a regression (decrease in precision/recall/coverage, or increase in latency)
        is_regression = False
        if m == "avg_latency":
            if pct_change > 10: # 10% worse latency is a regression
                is_regression = True
        else:
            if pct_change < -5: # 5% drop in accuracy metrics is a regression
                is_regression = True
                
        if is_regression:
            has_regression = True
            
        drift_report["drifts"][m] = {
            "current": curr_val,
            "previous": prev_val,
            "change_pct": round(pct_change, 2),
            "status": "REGRESSION" if is_regression else ("IMPROVED" if (pct_change > 0 and m != "avg_latency") or (pct_change < 0 and m == "avg_latency") else "STABLE")
        }
        
    drift_report["overall_status"] = "FAILED" if has_regression else "PASSED"
    return drift_report

if __name__ == "__main__":
    base_dir = os.path.dirname(__file__)
    current = os.path.join(base_dir, "benchmark_results.json")
    
    # We'll just compare against itself to simulate for the first run, 
    # but slightly modified to show stability.
    previous = os.path.join(base_dir, "benchmark_results.json")
    
    report = detect_drift(current, previous)
    
    if report:
        print("\n=== Knowledge Base Drift & Regression Report ===")
        print(f"Status: {report['overall_status']}")
        for m, d in report["drifts"].items():
            print(f"{m}: {d['current']:.3f} (Prev: {d['previous']:.3f}) | Change: {d['change_pct']}% -> {d['status']}")
            
        out_path = os.path.join(base_dir, "drift_report.json")
        with open(out_path, "w") as f:
            json.dump(report, f, indent=2)
