import json
import os

def main():
    print("Curating Baseline...")
    
    with open("knowledge_base_inventory.json", "r", encoding="utf-8") as f:
        inventory = json.load(f)
        
    # Select all documents for baseline
    selection = inventory
    
    with open("knowledge_base_selection.json", "w", encoding="utf-8") as f:
        json.dump(selection, f, indent=2)
        
    print(f"Selected {len(selection)} documents for the baseline.")

if __name__ == "__main__":
    main()
