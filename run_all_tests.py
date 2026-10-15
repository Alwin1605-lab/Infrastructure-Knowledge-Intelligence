import sys
import subprocess
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from tests.qa.failure_analyzer import FailureAnalyzer, FailureSeverity, FailureCategory
from tests.qa.knowledge_base_tests import run_integrity_tests

def run_script(script_name, analyzer, stage_name):
    print(f"\n--- Running {stage_name} ---")
    start_time = time.time()
    try:
        res = subprocess.run(["python", script_name], capture_output=True, text=True, timeout=120)
        elapsed = time.time() - start_time
        if res.returncode != 0:
            print(res.stdout)
            print(res.stderr)
            analyzer.record_failure(f"{stage_name} Script", script_name, f"Exit code {res.returncode}", 
                                    FailureCategory.TEST_TIMEOUT if "Timeout" in res.stderr else FailureCategory.UNKNOWN, 
                                    FailureSeverity.HIGH, traceback=res.stderr)
        else:
            print(f"{stage_name} completed in {elapsed:.2f}s")
    except subprocess.TimeoutExpired as e:
        analyzer.record_failure(f"{stage_name} Script", script_name, "Script timed out after 120s", 
                                FailureCategory.TEST_TIMEOUT, FailureSeverity.HIGH)
    except Exception as e:
        analyzer.record_failure(f"{stage_name} Script", script_name, str(e), 
                                FailureCategory.UNKNOWN, FailureSeverity.HIGH)

def run_pytest(analyzer):
    print("\n--- Running Pytest Suite ---")
    start_time = time.time()
    try:
        res = subprocess.run(["python", "-m", "pytest", "backend/tests/test_api.py", "-v", "--tb=short"], capture_output=True, text=True, timeout=300)
        if res.returncode != 0:
            print(res.stdout)
            analyzer.record_failure("Pytest API Tests", "pytest", "Pytest suite failed", 
                                    FailureCategory.API_ERROR, FailureSeverity.HIGH, traceback=res.stderr)
        else:
            print("Pytest completed successfully.")
    except subprocess.TimeoutExpired:
        analyzer.record_failure("Pytest Suite", "pytest", "Test suite timed out after 300s", 
                                FailureCategory.TEST_TIMEOUT, FailureSeverity.HIGH)

def main():
    print("=========================================")
    print("BUILDING KNOWLEDGE INTELLIGENCE SYSTEM")
    print("MASTER QA ORCHESTRATOR")
    print("=========================================")
    
    total_start = time.time()
    analyzer = FailureAnalyzer()
    
    # 1. Environment & Docker
    run_script("run_docker_tests.py", analyzer, "Docker Validation")
    run_script("run_smoke_tests.py", analyzer, "Smoke Tests")
    
    # 2. Pytest API Tests
    run_pytest(analyzer)
    
    # 3. Knowledge Base Integrity
    kb_metrics = run_integrity_tests(analyzer)
    if not kb_metrics:
        kb_metrics = {}
        
    # 4. E2E Tests
    print("\n--- Running Playwright E2E Tests ---")
    start_time = time.time()
    try:
        res = subprocess.run(["python", "-m", "pytest", "tests/e2e/test_workflows.py", "-v", "--tb=short"], capture_output=True, text=True, timeout=300)
        if res.returncode != 0:
            print(res.stdout)
            analyzer.record_failure("E2E Tests", "pytest playwright", "E2E suite failed", 
                                    FailureCategory.FRONTEND_ERROR, FailureSeverity.HIGH, traceback=res.stderr)
        else:
            print("E2E Tests completed successfully.")
    except subprocess.TimeoutExpired:
        analyzer.record_failure("E2E Suite", "pytest playwright", "E2E tests timed out after 300s", 
                                FailureCategory.TEST_TIMEOUT, FailureSeverity.HIGH)
    
    total_time = time.time() - total_start
    
    # Determine readiness
    critical_failures = [f for f in analyzer.failures if f["severity"] == FailureSeverity.CRITICAL.value]
    if critical_failures:
        readiness = "NOT_READY"
    elif analyzer.failures:
        readiness = "READY_WITH_WARNINGS"
    else:
        readiness = "PRODUCTION_READY"
        
    analyzer.generate_report(kb_metrics, total_time, readiness)
    analyzer.save_results()
    analyzer.save_analysis()
    analyzer.update_baseline(kb_metrics)
    
    print("\n========================================")
    print("BUILDING KNOWLEDGE INTELLIGENCE SYSTEM")
    print("QA SUMMARY")
    print("========================================")
    print(f"PASS: {analyzer.stats['Passed']}")
    print(f"FAIL: {analyzer.stats['Failed']}")
    print(f"SKIP: {analyzer.stats['Skipped']}")
    print(f"UNAVAILABLE: {analyzer.stats['Unavailable']}")
    print(f"TIMEOUT: {analyzer.stats['Timeouts']}")
    print(f"PARTIAL: {analyzer.stats['Partial']}")
    print(f"\nReadiness Status: {readiness}")
    print("\nCritical Issues:")
    for f in critical_failures:
        print(f" - {f['test']}: {f['error_message']}")
    print("\nQA Report: qa_report.md")
    print("Machine Results: qa_results.json")
    print("========================================")
    
if __name__ == "__main__":
    main()
