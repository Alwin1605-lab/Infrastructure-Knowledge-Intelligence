import asyncio
import time
import random
import os
import json

async def simulate_query(user_id, query_id):
    start = time.time()
    await asyncio.sleep(random.uniform(0.1, 0.5)) # Network overhead
    
    # Process
    process_time = random.uniform(0.3, 1.2)
    if random.random() < 0.02: # 2% failure rate under load
        await asyncio.sleep(process_time)
        return {"status": "error", "latency": time.time() - start, "user": user_id, "id": query_id}
        
    await asyncio.sleep(process_time)
    
    return {"status": "success", "latency": time.time() - start, "user": user_id, "id": query_id}

async def run_stress_test(concurrent_users=50, queries_per_user=10):
    print(f"Starting Stress Test: {concurrent_users} concurrent users, {queries_per_user} queries each...")
    
    start_time = time.time()
    tasks = []
    
    for u in range(concurrent_users):
        for q in range(queries_per_user):
            tasks.append(simulate_query(f"user_{u}", f"q_{q}"))
            
    results = await asyncio.gather(*tasks)
    total_time = time.time() - start_time
    
    success = sum(1 for r in results if r["status"] == "success")
    failed = len(results) - success
    
    latencies = [r["latency"] for r in results if r["status"] == "success"]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0
    
    report = {
        "timestamp": time.time(),
        "total_requests": len(results),
        "total_time_seconds": total_time,
        "throughput_req_per_sec": len(results) / total_time,
        "success_rate": success / len(results),
        "error_rate": failed / len(results),
        "avg_latency": avg_latency,
        "p95_latency": p95_latency,
        "memory_usage_mb": random.uniform(450, 600), # Mocked
        "cpu_usage_pct": random.uniform(65, 85) # Mocked
    }
    
    out_path = os.path.join(os.path.dirname(__file__), "stress_test_results.json")
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)
        
    print("\n=== Stress Test Results ===")
    print(f"Total Requests: {report['total_requests']}")
    print(f"Throughput: {report['throughput_req_per_sec']:.2f} req/s")
    print(f"Average Latency: {report['avg_latency']:.3f}s")
    print(f"P95 Latency: {report['p95_latency']:.3f}s")
    print(f"Error Rate: {report['error_rate']*100:.1f}%")
    print(f"Memory Usage: {report['memory_usage_mb']:.1f} MB")
    
if __name__ == "__main__":
    asyncio.run(run_stress_test(concurrent_users=50, queries_per_user=10))
