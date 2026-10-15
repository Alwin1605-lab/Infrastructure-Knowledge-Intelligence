import asyncio
import os
import sys
import json
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.config import get_settings
from app.models.document import Document
from app.models.acquisition import AcquiredDocument

async def export_snapshot():
    settings = get_settings()
    
    # Init MongoDB
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    await init_beanie(database=client[settings.MONGODB_DATABASE], document_models=[Document, AcquiredDocument])
    
    print("Exporting Knowledge Base Snapshot...")
    
    docs = await Document.find_all().to_list()
    acquired_docs = await AcquiredDocument.find_all().to_list()
    
    snapshot_data = {
        "export_date": datetime.utcnow().isoformat(),
        "total_documents": len(docs),
        "total_acquired_documents": len(acquired_docs),
        "documents": [],
        "acquired_documents": []
    }
    
    for doc in docs:
        doc_dict = doc.model_dump(exclude={"extracted_pages", "id"})
        doc_dict["_id"] = str(doc.id)
        # Convert enums to string
        doc_dict["status"] = doc_dict["status"].value if hasattr(doc_dict["status"], "value") else str(doc_dict["status"])
        doc_dict["document_type"] = doc_dict["document_type"].value if hasattr(doc_dict["document_type"], "value") else str(doc_dict["document_type"])
        snapshot_data["documents"].append(doc_dict)
        
    for doc in acquired_docs:
        doc_dict = doc.model_dump(exclude={"id"})
        doc_dict["_id"] = str(doc.id)
        doc_dict["status"] = doc_dict["status"].value if hasattr(doc_dict["status"], "value") else str(doc_dict["status"])
        snapshot_data["acquired_documents"].append(doc_dict)
        
    os.makedirs("snapshots", exist_ok=True)
    filename = f"snapshots/kb_snapshot_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(filename, "w") as f:
        json.dump(snapshot_data, f, indent=2, default=str)
        
    print(f"Snapshot exported successfully to: {filename}")

if __name__ == "__main__":
    asyncio.run(export_snapshot())
