from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from bson import ObjectId

from app.models.acquisition import AcquiredDocument, AcquisitionStatus
from app.services.acquisition_service import AcquisitionService
from app.services.gap_service import KnowledgeGapService
from app.api.deps import SettingsDep, ChromaIndexerDep, KGBuilderDep, CurrentUserDep

router = APIRouter(prefix="/acquisition", tags=["Acquisition"])

class SearchRequest(BaseModel):
    query: str = ""
    connector_type: str = "openalex"
    author: str = ""
    year: str = ""
    journal: str = ""
    limit: int = 50

class ImportDoiRequest(BaseModel):
    doi: str

@router.get("/queue")
async def list_queue():
    """List all acquired documents in the queue."""
    docs = await AcquiredDocument.find_all().to_list()
    return docs

@router.post("/search")
async def search_documents(req: SearchRequest):
    """Run search against a specific connector."""
    try:
        docs = await AcquisitionService.run_search(
            query=req.query, 
            connector_type=req.connector_type,
            author=req.author,
            year=req.year,
            journal=req.journal,
            limit=req.limit
        )
        return {"status": "success", "imported": len(docs), "documents": docs}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
from typing import List, Dict, Any

class BatchImportRequest(BaseModel):
    documents: List[Dict[str, Any]]

@router.post("/import/batch")
async def import_batch(req: BatchImportRequest):
    """Batch import documents from search preview into review queue."""
    try:
        saved_docs = []
        for metadata in req.documents:
            doc = AcquiredDocument(
                title=metadata.get("title"),
                authors=metadata.get("authors", []),
                year=metadata.get("year"),
                doi=metadata.get("doi"),
                source_url=metadata.get("source_url"),
                pdf_url=metadata.get("pdf_url"),
                status=AcquisitionStatus.METADATA_REVIEW
            )
            await doc.insert()
            saved_docs.append(doc)
        return {"status": "success", "imported": len(saved_docs)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/import/doi")
async def import_doi(req: ImportDoiRequest):
    """Import document by DOI."""
    try:
        doc = await AcquisitionService.import_doi(req.doi)
        return {"status": "success", "document": doc}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

from fastapi import UploadFile, File, Form
import os

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(None),
    source: str = Form("admin_upload"),
    category: str = Form("Proprietary Manual")
):
    """Upload a proprietary/licensed document directly to the acquisition review queue."""
    try:
        os.makedirs("uploads", exist_ok=True)
        filename = file.filename
        safe_title = title if title else filename
        
        # We will create a temporary AcquiredDocument
        doc = AcquiredDocument(
            title=safe_title,
            source=source,
            status=AcquisitionStatus.METADATA_REVIEW,
            category=category
        )
        await doc.insert()
        
        local_path = f"uploads/temp_{str(doc.id)}.pdf"
        with open(local_path, "wb") as buffer:
            buffer.write(await file.read())
            
        doc.local_file_path = local_path
        # Skip download step, go straight to FULL_REVIEW since we have the file
        doc.status = AcquisitionStatus.FULL_REVIEW
        await doc.save()
        
        return {"status": "success", "document": doc}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/queue/{id}/approve-download")
async def approve_download(id: str):
    """Approve document for download."""
    try:
        doc = await AcquisitionService.download_document(id)
        return {"status": "success", "document": doc}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/queue/{id}/approve-index")
async def approve_index(
    id: str,
    settings: SettingsDep,
    chroma_indexer: ChromaIndexerDep,
    kg_builder: KGBuilderDep,
    current_user: CurrentUserDep,
):
    """Approve document for indexing and queue it into the processing pipeline."""
    doc = await AcquiredDocument.get(ObjectId(id))
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if not getattr(doc, "local_file_path", None):
        raise HTTPException(status_code=400, detail="Document has not been downloaded yet")
        
    import builtins
    from app.services.document_service import DocumentService
    from app.models.document import DocumentType
    
    service = DocumentService(settings, chroma_indexer=chroma_indexer, kg_builder=kg_builder)
    
    try:
        with builtins.open(doc.local_file_path, "rb") as f:
            job = await service.upload_and_queue(
                file=f,
                filename=f"{doc.title}.pdf",
                content_type="application/pdf",
                document_type=DocumentType.RESEARCH,
                category="Engineering",
                owner_id=str(current_user.id),
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to queue document: {str(e)}")
    
    doc.status = AcquisitionStatus.INDEXED
    await doc.save()
    return {"status": "success", "document": doc, "job_id": str(job.id)}

@router.put("/queue/{id}/reject")
async def reject_document(id: str):
    """Reject a document."""
    doc = await AcquiredDocument.get(ObjectId(id))
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc.status = AcquisitionStatus.REJECTED
    await doc.save()
    return {"status": "success", "document": doc}

@router.get("/gaps")
async def get_gaps():
    """Get knowledge gaps."""
    gaps = await KnowledgeGapService.get_gaps()
    return gaps
