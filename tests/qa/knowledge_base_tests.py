import os
import pymongo
from neo4j import GraphDatabase
import json
import time

def run_integrity_tests(analyzer):
    print("====================")
    print("KNOWLEDGE BASE INTEGRITY TESTS")
    print("====================")
    
    # 1. Connect to DBs
    try:
        mongo = pymongo.MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=2000)
        db = mongo["infra_knowledge"]
        docs_collection = db["documents"]
        jobs_collection = db["processing_jobs"]
    except Exception as e:
        from tests.qa.failure_analyzer import FailureCategory, FailureSeverity
        analyzer.record_failure("KB MongoDB Connect", "mongodb://localhost:27017", str(e), 
                                FailureCategory.MONGODB_ERROR, FailureSeverity.CRITICAL)
        return

    try:
        neo4j_driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))
    except Exception as e:
        from tests.qa.failure_analyzer import FailureCategory, FailureSeverity
        analyzer.record_failure("KB Neo4j Connect", "bolt://localhost:7687", str(e), 
                                FailureCategory.NEO4J_ERROR, FailureSeverity.CRITICAL)
        return

    # Gather data
    kb_dir = "knowledge_base"
    fs_files = []
    for root, _, files in os.walk(kb_dir):
        for f in files:
            if f.endswith('.pdf'):
                fs_files.append(f)
                
    mongo_docs = {d['filename']: d for d in docs_collection.find()}
    mongo_jobs = {}
    for j in jobs_collection.find():
        if j['filename'] not in mongo_jobs or j['created_at'] > mongo_jobs[j['filename']]['created_at']:
            mongo_jobs[j['filename']] = j
            
    with neo4j_driver.session() as session:
        node_count = session.run("MATCH (n) RETURN count(n)").single()[0]
        rel_count = session.run("MATCH ()-[r]->() RETURN count(r)").single()[0]
        
    kb_metrics = {
        "Total Entities": {"value": node_count, "source": "live Neo4j query", "timestamp": time.time()},
        "Total Relationships": {"value": rel_count, "source": "live Neo4j query", "timestamp": time.time()}
    }

    report = ["# Knowledge Base Integrity Report\n", "| Document | File | MongoDB | Job Status | Neo4j | Overall Status |"]
    report.append("|---|---|---|---|---|---|")
    
    for filename in fs_files:
        fs_stat = "PASS"
        doc = mongo_docs.get(filename)
        job = mongo_jobs.get(filename)
        
        mongo_stat = "PASS" if doc else "FAIL"
        
        if not job:
            job_stat = "NOT_INDEXED"
            overall = "NOT_INDEXED"
        else:
            job_status = job.get('status', 'UNKNOWN')
            if job_status == "COMPLETED":
                job_stat = "PASS"
                overall = "COMPLETE"
            elif job_status == "FAILED":
                job_stat = "FAILED"
                overall = "PARTIAL" if doc else "FAILED"
            else:
                job_stat = job_status
                overall = "PARTIAL"
                
        neo4j_stat = "PASS" if (doc and doc.get('total_chunks', 0) > 0) else "UNKNOWN"
        if job and job.get('kg_nodes_created', 0) > 0:
            neo4j_stat = "PASS"
            
        report.append(f"| {filename} | {fs_stat} | {mongo_stat} | {job_stat} | {neo4j_stat} | {overall} |")
        
        if overall in ["FAILED", "PARTIAL"]:
            from tests.qa.failure_analyzer import FailureCategory, FailureSeverity
            analyzer.record_failure(f"KB Integrity: {filename}", "Integrity Check", 
                                    f"Status is {overall}. Job: {job_stat}", FailureCategory.DOCUMENT_PROCESSING_FAILED, FailureSeverity.MEDIUM)
            
    with open("docs/archive/knowledge_base_integrity_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report))
        
    print(f"Generated docs/archive/knowledge_base_integrity_report.md for {len(fs_files)} files.")
    return kb_metrics
