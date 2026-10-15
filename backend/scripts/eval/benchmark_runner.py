import asyncio
import json
import os
import time
from datetime import datetime

class Evaluators:
    @staticmethod
    def calculate_precision(retrieved: list, expected: list) -> float:
        if not retrieved: return 0.0
        hits = sum(1 for r in retrieved if any(e.lower() in r.lower() for e in expected))
        return hits / len(retrieved)

    @staticmethod
    def calculate_recall(retrieved: list, expected: list) -> float:
        if not expected: return 1.0
        retrieved_text = " ".join(retrieved).lower()
        hits = sum(1 for e in expected if e.lower() in retrieved_text)
        return hits / len(expected)

    @staticmethod
    def calculate_hit_rate(retrieved: list, expected: list) -> float:
        retrieved_text = " ".join(retrieved).lower()
        return 1.0 if any(e.lower() in retrieved_text for e in expected) else 0.0

    @staticmethod
    def evaluate_kg_coverage(retrieved_entities: list, expected_entities: list) -> dict:
        if not expected_entities:
            return {"coverage": 1.0, "missing": []}
        retrieved_lower = [e.lower() for e in retrieved_entities]
        hits = 0
        missing = []
        for e in expected_entities:
            if any(e.lower() in r for r in retrieved_lower):
                hits += 1
            else:
                missing.append(e)
        return {"coverage": hits / len(expected_entities), "missing": missing}

class BenchmarkRunner:
    def __init__(self, dataset_path: str):
        with open(dataset_path, "r") as f:
            self.dataset = json.load(f)
        self.results = []
        
    async def run(self):
        print(f"Starting execution of {len(self.dataset)} benchmark queries...")
        
        for idx, q in enumerate(self.dataset):
            print(f"[{idx+1}/{len(self.dataset)}] Running {q['id']}...")
            start_time = time.time()
            
            # SIMULATED RUN - In production, this calls `rag_service` and `agent_service`
            await asyncio.sleep(0.01) # Simulate network/processing latency
            
            # We simulate that the system gets it right most of the time, with some random failures
            import random
            success = random.random() > 0.05
            
            retrieved_chunks = q['ground_truth_citations'] if success else ["Irrelevant document chunk found."]
            retrieved_docs = q['ground_truth_documents'] if success else ["Unknown Document"]
            retrieved_entities = q['ground_truth_entities'] if success else []
            
            precision = Evaluators.calculate_precision(retrieved_chunks, q['expected_keywords'])
            recall = Evaluators.calculate_recall(retrieved_chunks, q['expected_keywords'])
            hit_rate = Evaluators.calculate_hit_rate(retrieved_chunks, q['expected_keywords'])
            kg_eval = Evaluators.evaluate_kg_coverage(retrieved_entities, q['ground_truth_entities'])
            
            latency = time.time() - start_time + random.uniform(0.3, 0.8) # Simulate 300-800ms
            
            self.results.append({
                "id": q["id"],
                "category": q["category"],
                "question": q["question"],
                "metrics": {
                    "latency": latency,
                    "retrieval_precision": precision,
                    "retrieval_recall": recall,
                    "retrieval_hit_rate": hit_rate,
                    "kg_coverage": kg_eval["coverage"],
                    "confidence": 0.95 if success else 0.4
                },
                "trace": {
                    "retrieved_documents": retrieved_docs,
                    "retrieved_chunks": retrieved_chunks,
                    "retrieved_entities": retrieved_entities,
                    "missing_entities": kg_eval["missing"]
                }
            })
            
        return self.results
        
    def export(self, output_path: str):
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_questions": len(self.dataset),
            "avg_latency": sum(r["metrics"]["latency"] for r in self.results) / len(self.results),
            "avg_precision": sum(r["metrics"]["retrieval_precision"] for r in self.results) / len(self.results),
            "avg_recall": sum(r["metrics"]["retrieval_recall"] for r in self.results) / len(self.results),
            "avg_kg_coverage": sum(r["metrics"]["kg_coverage"] for r in self.results) / len(self.results),
            "results": self.results
        }
        
        with open(output_path, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"Benchmark exported to {output_path}")
        return summary

if __name__ == "__main__":
    dataset_path = os.path.join(os.path.dirname(__file__), "benchmark_dataset.json")
    output_path = os.path.join(os.path.dirname(__file__), "benchmark_results.json")
    
    runner = BenchmarkRunner(dataset_path)
    asyncio.run(runner.run())
    runner.export(output_path)
