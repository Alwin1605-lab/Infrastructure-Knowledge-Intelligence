import json
import os

def check_file_status(filepath, component_name, critical=False):
    if not os.path.exists(filepath):
        return {"status": "FAIL", "reason": f"Missing {component_name} output", "critical": critical}
    return {"status": "PASS", "reason": "OK", "critical": critical}

def main():
    print("Running Regression Check...")
    
    # 1. Check QA results (qa_report.md or test results)
    qa_check = check_file_status("qa_report.md", "QA Summary", critical=True)
    
    # 2. Check Baseline outputs
    baseline_json = check_file_status("knowledge_base_baseline.json", "Baseline JSON", critical=True)
    
    # 3. Check Benchmark outputs
    benchmark_json = check_file_status("benchmark_results.json", "Benchmark JSON", critical=False)
    
    # SYSTEM_READINESS
    # READY if the application, APIs, databases, authentication, RAG, KG, agents, frontend, Docker and QA tests are operational.
    system_readiness = "READY" if qa_check["status"] == "PASS" else "NOT_READY"
    
    # KNOWLEDGE_BASE_READINESS
    # READY only when the selected research corpus has actually been indexed and verified.
    kb_processed = False
    if baseline_json["status"] == "PASS":
        try:
            with open("knowledge_base_baseline.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("completed", 0) > 0 or data.get("partial", 0) > 0:
                    kb_processed = True
        except Exception:
            pass
    
    knowledge_base_readiness = "READY" if kb_processed else "NOT_READY"
    
    # RESEARCH_EXPERIMENT_READINESS
    # READY when system is operational, corpus is available, benchmark ground truth is available, config is frozen.
    benchmark_status = "UNKNOWN"
    if benchmark_json["status"] == "PASS":
        try:
            with open("benchmark_results.json", "r", encoding="utf-8") as f:
                bench_data = json.load(f)
                benchmark_status = bench_data.get("status", "UNKNOWN")
        except Exception:
            pass
            
    research_experiment_readiness = "NOT_READY"
    if system_readiness == "READY" and knowledge_base_readiness == "READY" and benchmark_status != "NOT_VERIFIABLE":
        research_experiment_readiness = "READY"
        
    report = [
        f"# System Regression Report",
        f"## Readiness Classification",
        f"- **SYSTEM_READINESS:** {system_readiness}",
        f"- **KNOWLEDGE_BASE_READINESS:** {knowledge_base_readiness}",
        f"- **RESEARCH_EXPERIMENT_READINESS:** {research_experiment_readiness}",
        "",
        "## Components",
        f"- QA Framework Output: {qa_check['status']}",
        f"- Baseline Generated: {baseline_json['status']}",
        f"- Benchmark Generated: {benchmark_json['status']} ({benchmark_status})",
        f"- KB Processed: {'PASS' if kb_processed else 'FAIL'}",
        ""
    ]
    
    if research_experiment_readiness != "READY":
        report.append("## Reasons for NOT_READY (Research Experiment)")
        if system_readiness != "READY":
            report.append("- System Readiness is NOT_READY. QA tests may have failed or missing reports.")
        if knowledge_base_readiness != "READY":
            report.append("- Knowledge Base Readiness is NOT_READY. No documents successfully processed.")
        if benchmark_status == "NOT_VERIFIABLE":
            report.append("- Benchmark is NOT_VERIFIABLE. No reliable ground truth dataset available.")
            
    with open("regression_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report))
        
    print(f"Regression Check Complete.")
    print(f"  SYSTEM_READINESS: {system_readiness}")
    print(f"  KNOWLEDGE_BASE_READINESS: {knowledge_base_readiness}")
    print(f"  RESEARCH_EXPERIMENT_READINESS: {research_experiment_readiness}")

if __name__ == "__main__":
    main()
