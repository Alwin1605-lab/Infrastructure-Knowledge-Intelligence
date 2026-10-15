import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
import sys
import os

# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.acquisition import SourceRegistry, AcquiredDocument, AcquisitionTask, AcquisitionStatus
from app.models.document import Document
from app.services.acquisition_service import AcquisitionService
from app.config import get_settings

async def main():
    settings = get_settings()
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    
    # Check if models module exists before importing
    models_to_init = [SourceRegistry, AcquiredDocument, AcquisitionTask, Document]
    try:
        from app.models.processing_job import ProcessingJob
        from app.models.query_metric import QueryMetric
        from app.models.saved_search import SavedSearch
        from app.models.notification import Notification
        models_to_init.extend([ProcessingJob, QueryMetric, SavedSearch, Notification])
    except ImportError:
        pass
        
    await init_beanie(database=client[settings.MONGODB_DATABASE], document_models=models_to_init)
    
    print("Initializing Knowledge Base Acquisition Pipeline...")
    service = AcquisitionService()
    
    # 1. Search for some key civil engineering topics
    topics = ["concrete carbonation repair", "seismic retrofitting of RC columns"]
    
    for topic in topics:
        print(f"\n[1/4] Searching OpenAlex for: '{topic}'")
        try:
            await service.run_search(topic, "openalex")
        except Exception as e:
            print(f"Error during search: {e}")

    # 2. Find newly acquired documents in METADATA_REVIEW
    docs = await AcquiredDocument.find(AcquiredDocument.status == AcquisitionStatus.METADATA_REVIEW).to_list()
    print(f"\n[2/4] Found {len(docs)} documents in Review Queue.")
    
    if not docs:
        print("No open-access PDFs found for these topics.")
        return

    # 3. Approve up to 3 documents for download (simulating Admin action)
    for i, doc in enumerate(docs[:3]):
        print(f"\n[3/4] Approving Download for [{i+1}/3]: {doc.title}")
        try:
            # This triggers download, LLM classification, and sets to FULL_REVIEW
            await service.download_document(str(doc.id))
        except Exception as e:
            print(f"Error downloading: {e}")
            
    # 4. Approve them for indexing (simulating Admin action)
    downloaded = await AcquiredDocument.find(AcquiredDocument.status == AcquisitionStatus.FULL_REVIEW).to_list()
    print(f"\n[4/4] Found {len(downloaded)} documents ready for indexing.")
    
    for doc in downloaded:
        print(f"Approving Indexing for: {doc.title} (AI Score: {doc.relevance_score})")
        doc.status = AcquisitionStatus.INDEXED
        await doc.save()

    print("\n✅ Knowledge Base Successfully Increased!")

if __name__ == "__main__":
    asyncio.run(main())
