import json
import os
from typing import Dict, List, Any, Optional
from enum import Enum
from datetime import datetime

class FailureSeverity(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class FailureCategory(Enum):
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    PATH_ERROR = "PATH_ERROR"
    API_ERROR = "API_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    CHROMADB_ERROR = "CHROMADB_ERROR"
    NEO4J_ERROR = "NEO4J_ERROR"
    MONGODB_ERROR = "MONGODB_ERROR"
    DOCUMENT_MISSING = "DOCUMENT_MISSING"
    DOCUMENT_PROCESSING_FAILED = "DOCUMENT_PROCESSING_FAILED"
    EMBEDDING_FAILED = "EMBEDDING_FAILED"
    KG_EXTRACTION_FAILED = "KG_EXTRACTION_FAILED"
    GROQ_RATE_LIMIT = "GROQ_RATE_LIMIT"
    GROQ_TIMEOUT = "GROQ_TIMEOUT"
    RAG_RETRIEVAL_FAILURE = "RAG_RETRIEVAL_FAILURE"
    AGENT_FAILURE = "AGENT_FAILURE"
    FRONTEND_ERROR = "FRONTEND_ERROR"
    DOCKER_ERROR = "DOCKER_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    TEST_TIMEOUT = "TEST_TIMEOUT"
    UNKNOWN = "UNKNOWN"

class FailureAnalyzer:
    def __init__(self):
        self.failures = []
        self.results_file = "docs/archive/qa_results.json"
        self.report_file = "docs/archive/qa_report.md"
        self.baseline_file = "docs/archive/qa_baseline.json"
        self.analysis_file = "docs/archive/failure_analysis.md"
        self.kb_integrity_file = "docs/archive/knowledge_base_integrity_report.md"
        self.stats = {
            "Total Tests": 0,
            "Passed": 0,
            "Failed": 0,
            "Skipped": 0,
            "Unavailable": 0,
            "Timeouts": 0,
            "Partial": 0,
            "Not Verifiable": 0
        }
        
    def add_result(self, status: str):
        if status == "PASS":
            self.stats["Passed"] += 1
        elif status == "FAIL":
            self.stats["Failed"] += 1
        elif status == "SKIPPED":
            self.stats["Skipped"] += 1
        elif status == "UNAVAILABLE":
            self.stats["Unavailable"] += 1
        elif status == "TIMEOUT":
            self.stats["Timeouts"] += 1
        elif status == "PARTIAL":
            self.stats["Partial"] += 1
        elif status == "NOT_VERIFIABLE":
            self.stats["Not Verifiable"] += 1
            
        self.stats["Total Tests"] += 1

    def record_failure(self, test: str, endpoint: str, error_message: str, category: FailureCategory, severity: FailureSeverity, traceback: Optional[str] = None, suggested_fix: str = ""):
        self.add_result("FAIL")
        failure = {
            "test": test,
            "endpoint": endpoint,
            "error_message": error_message,
            "category": category.value,
            "severity": severity.value,
            "traceback": traceback,
            "suggested_fix": suggested_fix,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.failures.append(failure)
        
    def save_analysis(self):
        with open(self.analysis_file, "w", encoding="utf-8") as f:
            f.write("# Failure Analysis Report\n\n")
            if not self.failures:
                f.write("No failures recorded!\n")
                return
            
            categories = {}
            for fail in self.failures:
                cat = fail["category"]
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(fail)
                
            for cat, fails in categories.items():
                f.write(f"## {cat} ({len(fails)} issues)\n")
                for fail in fails:
                    f.write(f"- **Test**: {fail['test']}\n")
                    f.write(f"  - **Endpoint**: {fail['endpoint']}\n")
                    f.write(f"  - **Severity**: {fail['severity']}\n")
                    f.write(f"  - **Error**: `{fail['error_message']}`\n")
                    if fail['suggested_fix']:
                        f.write(f"  - **Suggested Fix**: {fail['suggested_fix']}\n")
                    f.write("\n")

    def save_results(self):
        results = {
            "stats": self.stats,
            "failures": self.failures,
            "timestamp": datetime.utcnow().isoformat()
        }
        with open(self.results_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=4)
            
    def generate_report(self, kb_metrics: dict, execution_time: float, readiness_status: str):
        with open(self.report_file, "w", encoding="utf-8") as f:
            f.write("# QA Executive Summary\n\n")
            f.write("## Overall Statistics\n")
            f.write(f"- **Total Execution Time**: {execution_time:.2f}s\n")
            f.write(f"- **Total Tests**: {self.stats['Total Tests']}\n")
            f.write(f"- **Passed**: {self.stats['Passed']}\n")
            f.write(f"- **Failed**: {self.stats['Failed']}\n")
            f.write(f"- **Skipped**: {self.stats['Skipped']}\n")
            f.write(f"- **Unavailable**: {self.stats['Unavailable']}\n")
            f.write(f"- **Timeouts**: {self.stats['Timeouts']}\n")
            f.write(f"- **Partial**: {self.stats['Partial']}\n")
            f.write(f"- **Not Verifiable**: {self.stats['Not Verifiable']}\n\n")
            
            f.write("## Knowledge Base Statistics\n")
            for k, v in kb_metrics.items():
                f.write(f"- **{k}**: {v['value']} (Source: {v['source']}, Timestamp: {v['timestamp']})\n")
            
            f.write("\n## Readiness Status\n")
            f.write(f"> [!IMPORTANT]\n> **Status**: {readiness_status}\n\n")
            
            if self.failures:
                f.write("## Critical Issues\n")
                for fail in [f for f in self.failures if f["severity"] == FailureSeverity.CRITICAL.value]:
                    f.write(f"- **{fail['test']}**: {fail['error_message']} ({fail['category']})\n")

    def update_baseline(self, kb_metrics: dict):
        baseline = {
            "kb_metrics": kb_metrics,
            "timestamp": datetime.utcnow().isoformat()
        }
        with open(self.baseline_file, "w", encoding="utf-8") as f:
            json.dump(baseline, f, indent=4)
