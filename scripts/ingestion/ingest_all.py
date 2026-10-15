import os
import time
import requests
from pathlib import Path

API_BASE = "http://localhost:8000/api/v1"
KNOWLEDGE_BASE_DIR = Path("D:/Sem 7 Project/Project/knowledge_base")
USERNAME = "admin@buildknowledge.ai"
PASSWORD = "ChangeMe123!"

def get_token():
    print("Authenticating...")
    response = requests.post(f"{API_BASE}/auth/login", data={"username": USERNAME, "password": PASSWORD})
    if response.status_code != 200:
        print(f"Failed to authenticate: {response.text}")
        exit(1)
    return response.json()["access_token"]

def get_existing_filenames(token):
    print("Fetching existing documents...")
    headers = {"Authorization": f"Bearer {token}"}
    existing = set()
    skip = 0
    limit = 50
    while True:
        res = requests.get(f"{API_BASE}/documents?skip={skip}&limit={limit}", headers=headers)
        if res.status_code != 200:
            print(f"Failed to list documents: {res.text}")
            break
        data = res.json()
        docs = data.get("documents", [])
        if not docs:
            break
        for doc in docs:
            existing.add(doc["filename"])
        if skip + limit >= data.get("total", 0):
            break
        skip += limit
    print(f"Found {len(existing)} existing documents.")
    return existing

def poll_job(job_id, filename):
    global token
    headers = {"Authorization": f"Bearer {token}"}
    safe_filename = filename.encode('ascii', 'replace').decode('ascii')
    while True:
        try:
            res = requests.get(f"{API_BASE}/documents/jobs/{job_id}", headers=headers, timeout=10)
        except requests.exceptions.RequestException as e:
            print(f"[{safe_filename}] Backend connection lost during polling: {e}")
            return "FAILED", {"failed_step": "Backend Crash", "error_message": str(e)}
            
        if res.status_code == 401 or "credentials" in res.text:
            print(f"[{safe_filename}] Token expired, refreshing...")
            try:
                token = get_token()
                headers = {"Authorization": f"Bearer {token}"}
            except Exception as e:
                print(f"[{safe_filename}] Failed to refresh token: {e}")
            continue
            
        if res.status_code != 200:
            print(f"[{safe_filename}] Failed to poll job: {res.text}")
            return "FAILED", {"failed_step": "Polling", "error_message": res.text}
        
        job = res.json()
        status = job["status"]
        if status in ["COMPLETED", "FAILED"]:
            return status, job
        
        time.sleep(5)

def main():
    global token
    token = get_token()
    existing = get_existing_filenames(token)
    
    pdfs = list(KNOWLEDGE_BASE_DIR.rglob("*.pdf"))
    print(f"Found {len(pdfs)} PDFs in knowledge_base/")
    
    results = []
    queued_count = 0
    for i, pdf_path in enumerate(pdfs, 1):
        filename = pdf_path.name
        # Safe print for unicode characters in Windows CMD
        safe_filename = filename.encode('ascii', 'replace').decode('ascii')
        
        if filename in existing:
            print(f"[{i}/{len(pdfs)}] Skipping {safe_filename} (Already exists)")
            continue
            
        print(f"[{i}/{len(pdfs)}] Uploading {safe_filename}...")
        
        while True:
            with open(pdf_path, "rb") as f:
                headers = {"Authorization": f"Bearer {token}"}
                files = {"file": (filename, f, "application/pdf")}
                data = {"document_type": "general", "category": "general"}
                
                try:
                    res = requests.post(f"{API_BASE}/documents/upload-async", headers=headers, files=files, data=data)
                except Exception as e:
                    print(f"[{safe_filename}] Upload failed (backend might be down): {e}. Retrying in 10s...")
                    time.sleep(10)
                    continue
                    
            if res.status_code == 401 or "credentials" in res.text:
                print(f"[{safe_filename}] Token expired during upload, refreshing...")
                token = get_token()
                continue
                
            if res.status_code in [404, 502, 503]:
                print(f"[{safe_filename}] Backend returned {res.status_code}, might be restarting. Retrying in 10s...")
                time.sleep(10)
                continue
            
            break
            
        if results and results[-1]["filename"] == filename and results[-1]["status"] == "FAILED":
            continue
                
        if res.status_code != 202:
            print(f"[{safe_filename}] Upload rejected: {res.text}")
            results.append({"filename": filename, "status": "FAILED", "error": res.text})
            continue
            
        queued_count += 1
        job_id = res.json()["job_id"]
        print(f"[{safe_filename}] Queued as job {job_id}. Polling for completion...")
        
        status, job = poll_job(job_id, filename)
        
        if status == "COMPLETED":
            print(f"[{safe_filename}] SUCCESS: Extracted {job['pages_extracted']} pages, {job['chunks_created']} chunks, {job['kg_nodes_created']} nodes.")
        else:
            print(f"[{safe_filename}] FAILED at step {job.get('failed_step')}: {job.get('error_message')}")
            
        results.append({
            "filename": filename,
            "status": status,
            "job": job
        })
        
    print("\n\n--- INGESTION SUMMARY ---")
    completed = [r for r in results if r["status"] == "COMPLETED"]
    failed = [r for r in results if r["status"] == "FAILED"]
    print(f"Total processed: {len(results)}")
    print(f"Success: {len(completed)}")
    print(f"Failed: {len(failed)}")
    
    if failed:
        print("\nFailures:")
        for f in failed:
            job = f.get("job", {})
            step = job.get("failed_step", "Unknown") if isinstance(job, dict) else "Unknown"
            err = job.get("error_message", f.get("error", "Unknown")) if isinstance(job, dict) else f.get("error", "Unknown")
            safe_f = f['filename'].encode('ascii', 'replace').decode('ascii')
            print(f" - {safe_f} (Failed at {step}): {err}")

if __name__ == "__main__":
    main()
