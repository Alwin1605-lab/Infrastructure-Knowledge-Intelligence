import requests
import pymongo
from neo4j import GraphDatabase
import chromadb
import sys
import time

def check_service(name, check_fn):
    print(f"Checking {name}...", end=" ")
    try:
        start_time = time.time()
        result = check_fn()
        latency = time.time() - start_time
        if result:
            print(f"PASS ({latency:.2f}s)")
            return True, latency
        else:
            print("FAIL")
            return False, latency
    except Exception as e:
        print(f"FAIL ({e})")
        return False, 0.0

def main():
    print("====================")
    print("SMOKE TESTS")
    print("====================")
    
    success = True
    
    # 1. Frontend
    def check_frontend():
        res = requests.get("http://localhost:5173", timeout=5)
        return res.status_code == 200
    ok, _ = check_service("Frontend (:5173)", check_frontend)
    success = success and ok
    
    # 2. Backend Health
    def check_backend():
        res = requests.get("http://localhost:8000/api/v1/health/system", timeout=5)
        if res.status_code == 200:
            data = res.json()
            return data.get("status") == "ok"
        return False
    ok, _ = check_service("Backend (:8000)", check_backend)
    success = success and ok

    # 3. MongoDB
    def check_mongo():
        client = pymongo.MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=2000)
        client.admin.command('ping')
        return True
    ok, _ = check_service("MongoDB (:27017)", check_mongo)
    success = success and ok
    
    # 4. Neo4j
    def check_neo4j():
        driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))
        with driver.session() as session:
            result = session.run("RETURN 1")
            return result.single()[0] == 1
    ok, _ = check_service("Neo4j (:7687)", check_neo4j)
    success = success and ok

    print("====================")
    if success:
        print("SMOKE TESTS PASSED!")
        sys.exit(0)
    else:
        print("SMOKE TESTS FAILED!")
        sys.exit(1)

if __name__ == "__main__":
    main()
