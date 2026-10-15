import subprocess
import time
import sys
import os

def check_container_running(name):
    try:
        res = subprocess.run(["docker", "ps", "--filter", f"name={name}", "--format", "{{.Status}}"], capture_output=True, text=True)
        return "Up" in res.stdout
    except Exception:
        return False

def check_container_healthy(name):
    try:
        res = subprocess.run(["docker", "inspect", "--format", "{{.State.Health.Status}}", name], capture_output=True, text=True)
        return "healthy" in res.stdout
    except Exception:
        # Some containers don't have healthchecks, just checking if running
        return check_container_running(name)

def main():
    print("====================")
    print("DOCKER ORCHESTRATION TESTS")
    print("====================")
    
    # 1. Check docker-compose config
    print("Checking docker-compose config...", end=" ")
    res = subprocess.run(["docker-compose", "config", "-q"], capture_output=True)
    if res.returncode == 0:
        print("PASS")
    else:
        print("FAIL")
        sys.exit(1)

    containers = ["infra_frontend", "infra_backend", "infra_mongodb", "infra_neo4j", "infra_chromadb"]
    
    success = True
    for c in containers:
        print(f"Checking {c} running...", end=" ")
        if check_container_running(c):
            print("PASS")
        else:
            print("FAIL")
            success = False
            
        print(f"Checking {c} healthy...", end=" ")
        if check_container_healthy(c):
            print("PASS")
        else:
            print("FAIL")
            success = False

    print("====================")
    if success:
        print("DOCKER TESTS PASSED!")
        sys.exit(0)
    else:
        print("DOCKER TESTS FAILED!")
        sys.exit(1)

if __name__ == "__main__":
    main()
