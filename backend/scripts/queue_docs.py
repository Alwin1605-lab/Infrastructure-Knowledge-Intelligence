import asyncio, builtins, os
import httpx

os.environ["MONGODB_URI"] = "mongodb://localhost:27017"
os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["CHROMADB_HOST"] = "localhost"

from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.models import ALL_MODELS
from app.models.acquisition import AcquiredDocument, AcquisitionStatus
from app.services.document_service import DocumentService
from app.models.document import DocumentType, DocumentCategory
from app.config import get_settings
from app.vectorstore.connection import init_vectorstore
from app.knowledge_graph.connection import init_kg
from app.llm import create_llm_provider
from app.embedding import HuggingFaceEmbeddingService

async def process():
    settings = get_settings()
    settings.CHROMADB_HOST = "localhost"
    settings.NEO4J_URI = "bolt://localhost:7687"
    
    # Init DB
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    await init_beanie(database=client[settings.MONGODB_DATABASE], document_models=ALL_MODELS)
    
    # Init vector & KG
    chroma = await init_vectorstore(settings)
    await init_kg(settings)
    
    llm = create_llm_provider(settings)
    embed = HuggingFaceEmbeddingService(settings)
    
    from app.knowledge_graph.builder import KGBuilder
    kg_builder = KGBuilder(llm_provider=llm)
    
    service = DocumentService(settings, chroma_indexer=None, kg_builder=kg_builder)
    
    docs = await AcquiredDocument.find_all().to_list()
    
    for d in docs:
        if d.local_file_path and d.status == AcquisitionStatus.INDEXED:
            print(f'Queueing {d.title}...')
            with builtins.open(d.local_file_path, 'rb') as f:
                job = await service.upload_and_queue(
                    file=f,
                    filename=f'{d.title}.pdf',
                    content_type='application/pdf',
                    document_type=DocumentType.RESEARCH_PAPER,
                    category=DocumentCategory.RESEARCH,
                    owner_id='system',
                )
                print(f'Success Queueing: {job.id}')
                
                print(f'Processing {d.title}...')
                await service._process_document_background(str(job.id))
                print(f'Finished Processing: {d.title}!')
                
asyncio.run(process())
