import json
import os

def generate_readiness():
    print("Generating Research Readiness Report...")
    
    # Check System Readiness
    system_ready = os.path.exists("qa_report.md")
    
    # Check Knowledge Base Readiness
    kb_ready = False
    if os.path.exists("research_corpus.json"):
        try:
            with open("research_corpus.json", "r", encoding="utf-8") as f:
                corpus = json.load(f)
                if len(corpus.get("selected_documents", [])) > 1:
                    kb_ready = True
        except Exception:
            pass
            
    # Check Research Readiness
    benchmark_ready = False
    if os.path.exists("benchmark_validation_report.md"):
        try:
            with open("benchmark_validation_report.md", "r", encoding="utf-8") as f:
                report = f.read()
                if "Status: PASS" in report:
                    benchmark_ready = True
        except Exception:
            pass
            
    research_ready = system_ready and kb_ready and benchmark_ready
    
    status_str = "READY" if research_ready else "NOT_READY"
    
    content = [
        "# Research Experiment Readiness Report",
        "",
        f"**Final Status:** {status_str}",
        "",
        "## Component Status",
        f"- **SYSTEM_READINESS:** {'READY' if system_ready else 'NOT_READY'}",
        f"- **KNOWLEDGE_BASE_READINESS:** {'READY' if kb_ready else 'NOT_READY'}",
        f"- **RESEARCH_EXPERIMENT_READINESS:** {status_str}",
        "",
        "## Notes",
        "If RESEARCH_EXPERIMENT_READINESS is NOT_READY, it means the corpus is either too small or the benchmark questions fail validation."
    ]
    
    if status_str == "READY":
        content.append("> [!TIP]")
        content.append("> The system is fully ready for the final research experiment.")
        
    with open("research_readiness_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(content))
        
    print("Generated research_readiness_report.md")

if __name__ == "__main__":
    generate_readiness()
