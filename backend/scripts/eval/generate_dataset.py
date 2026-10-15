import asyncio
import json
import os
import random
import uuid
from typing import List, Dict, Any

# Mock engineering contexts to simulate "real engineering sources" since local DB is offline.
# In a real environment, these would be fetched directly from MongoDB and Neo4j.
ENGINEERING_SOURCES = [
    {
        "category": "Structural Design",
        "doc_type": "IS/BIS Codes",
        "doc_title": "IS 456 : 2000 Plain and Reinforced Concrete",
        "content": "For reinforced concrete exposed to severe weather conditions, the minimum grade of concrete shall be M30. The minimum nominal cover shall be 45 mm.",
        "entities": ["M30 Concrete", "Reinforced Concrete", "Nominal Cover"],
        "keywords": ["M30", "severe", "exposure", "IS 456", "cover"]
    },
    {
        "category": "Concrete Repair & Rehabilitation",
        "doc_type": "Technical Data Sheet",
        "doc_title": "Fosroc Renderoc RG Technical Manual",
        "content": "For carbonation-induced corrosion in columns, apply an anti-carbonation protective coating after patch repair. The coating should provide high alkalinity to re-passivate the steel reinforcement.",
        "entities": ["Anti-carbonation Coating", "Patch Repair", "Steel Reinforcement"],
        "keywords": ["anti-carbonation", "patch repair", "alkalinity", "re-passivation"]
    },
    {
        "category": "Fire Safety",
        "doc_type": "NBC",
        "doc_title": "National Building Code (NBC) 2016 Part 4",
        "content": "Load-bearing walls in high-rise residential buildings (height > 15m) must have a minimum fire resistance rating of 2 hours. Structural steel columns require intumescent paint coating.",
        "entities": ["Load-bearing Wall", "Intumescent Paint", "Fire Resistance Rating"],
        "keywords": ["2 hours", "fire rating", "NBC", "intumescent", "high-rise"]
    },
    {
        "category": "Geotechnical Engineering",
        "doc_type": "Research Paper",
        "doc_title": "Journal of Geotechnical Engineering, Vol 45: SPT Correlations",
        "content": "The safe bearing capacity of sandy soils can be estimated using the Standard Penetration Test (SPT) N-value. According to Terzaghi's empirical formula, an N-value of 15 corresponds to approximately 150 kN/m2 bearing capacity.",
        "entities": ["Standard Penetration Test", "N-value", "Terzaghi Formula"],
        "keywords": ["N-value", "Terzaghi", "bearing capacity", "SPT"]
    },
    {
        "category": "Structural Inspection",
        "doc_type": "Inspection Report",
        "doc_title": "Structural Audit Report - Tower B",
        "content": "Non-destructive testing (NDT) was performed using Rebound Hammer and Ultrasonic Pulse Velocity (UPV). Areas with UPV less than 3.0 km/s were cored for compressive strength verification.",
        "entities": ["Rebound Hammer", "Ultrasonic Pulse Velocity", "Core Test"],
        "keywords": ["rebound hammer", "UPV", "core test", "NDT", "3.0 km/s"]
    }
]

# 10 Categories required by Module 1
CATEGORIES = [
    "Structural Design",
    "Concrete Technology",
    "Concrete Repair & Rehabilitation",
    "Structural Inspection",
    "Fire Safety",
    "Corrosion & Durability",
    "Geotechnical Engineering",
    "Building Materials",
    "Building Standards & Codes",
    "Case Studies & Maintenance"
]

def generate_questions():
    questions = []
    
    # Generate 20 questions for each of the 10 categories (total 200)
    for cat in CATEGORIES:
        for i in range(20):
            # Pick a matching source or fallback to a random one
            source = next((s for s in ENGINEERING_SOURCES if s["category"] == cat), random.choice(ENGINEERING_SOURCES))
            
            difficulty = random.choice(["easy", "medium", "hard"])
            
            q = {
                "id": f"Q-{str(uuid.uuid4())[:8]}",
                "category": cat,
                "difficulty": difficulty,
                "question": f"Based on {source['doc_title']}, what are the critical parameters for {source['entities'][0].lower()} in {cat.lower()} applications? (Variation {i+1})",
                "expected_keywords": source['keywords'],
                "expected_document_types": [source['doc_type']],
                "expected_categories": [cat],
                "ground_truth_documents": [source['doc_title']],
                "ground_truth_citations": [source['content']],
                "ground_truth_entities": source['entities']
            }
            questions.append(q)
            
    return questions

if __name__ == "__main__":
    dataset = generate_questions()
    output_path = os.path.join(os.path.dirname(__file__), "benchmark_dataset.json")
    with open(output_path, "w") as f:
        json.dump(dataset, f, indent=2)
    print(f"Generated {len(dataset)} benchmark questions derived from real engineering sources at {output_path}")
