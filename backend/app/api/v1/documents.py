"""Document upload and management API endpoints.

Provides REST endpoints for:
    - POST /documents/upload      — Upload a PDF document
    - GET  /documents             — List all documents
    - GET  /documents/{id}        — Get document details
    - DELETE /documents/{id}      — Delete a document
"""

from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile, HTTPException, Query

from app.api.deps import SettingsDep, ChromaIndexerDep, KGBuilderDep, CurrentUserDep
from app.core.exceptions import DocumentNotFoundError, DocumentUploadError, DocumentExtractionError
from app.core.logging import get_logger
from app.models.document import DocumentType, DocumentStatus
from app.schemas.document import (
    DocumentUploadResponse,
    DocumentSummary,
    DocumentDetail,
    DocumentListResponse,
)
from app.services.document_service import DocumentService

logger = get_logger(__name__)

router = APIRouter()


@router.post("/upload", response_model=DocumentUploadResponse, status_code=201)
async def upload_document(
    settings: SettingsDep,
    chroma_indexer: ChromaIndexerDep,
    kg_builder: KGBuilderDep,
    current_user: CurrentUserDep,
    file: UploadFile = File(..., description="PDF file to upload."),
    document_type: DocumentType = Form(
        default=DocumentType.GENERAL,
        description="Type/category of the building document.",
    ),
):
    """Upload a PDF building engineering document for processing.

    The document will be:
    1. Saved to the server
    2. Text extracted with page/section metadata
    3. Stored in MongoDB
    4. Chunked into overlapping segments
    5. Embedded using HuggingFace all-MiniLM-L6-v2
    6. Indexed in ChromaDB for semantic retrieval
    7. Entities extracted & indexed into Neo4j Building KG
    """
    if str(getattr(current_user, 'role', '')).lower() not in ["admin", "administrator"]:
        raise HTTPException(status_code=403, detail="Only administrators can manage the Global Knowledge Base")
        
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")

    service = DocumentService(settings, chroma_indexer=chroma_indexer, kg_builder=kg_builder)

    try:
        document = await service.upload_document(
            file=file.file,
            filename=file.filename,
            content_type=file.content_type or "application/pdf",
            document_type=document_type,
        )
    except DocumentUploadError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc
    except DocumentExtractionError as exc:
        raise HTTPException(status_code=422, detail=exc.message) from exc

    return DocumentUploadResponse(
        id=str(document.id),
        filename=document.filename,
        file_size_bytes=document.file_size_bytes,
        document_type=document.document_type,
        status=document.status,
        message=(
            f"Document '{document.filename}' uploaded and processed successfully. "
            f"{document.total_pages} pages extracted, {document.total_chunks} chunks indexed."
        ),
        created_at=document.created_at,
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    settings: SettingsDep,
    current_user: CurrentUserDep,
    skip: int = Query(default=0, ge=0, description="Pagination offset."),
    limit: int = Query(default=50, ge=1, le=100, description="Page size."),
    status: Optional[DocumentStatus] = Query(
        default=None, description="Filter by processing status."
    ),
):
    """List all uploaded documents with pagination.

    Returns a paginated list of document summaries sorted by
    upload date (newest first).
    """
    service = DocumentService(settings)
    documents, total = await service.list_documents(skip=skip, limit=limit, status=status)

    return DocumentListResponse(
        documents=[
            DocumentSummary(
                id=str(doc.id),
                filename=doc.filename,
                document_type=doc.document_type,
                status=doc.status,
                total_pages=doc.total_pages,
                total_chunks=doc.total_chunks,
                file_size_bytes=doc.file_size_bytes,
                created_at=doc.created_at,
                updated_at=doc.updated_at,
            )
            for doc in documents
        ],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/stats")
async def get_kb_stats(current_user: CurrentUserDep):
    """Get knowledge base statistics."""
    from app.services.analytics_service import AnalyticsService
    svc = AnalyticsService()
    return await svc.get_kb_stats()


@router.get("/jobs")
async def list_processing_jobs(
    settings: SettingsDep,
    current_user: CurrentUserDep,
    limit: int = Query(default=20, le=50),
    status: Optional[str] = Query(default=None),
):
    """List document processing jobs."""
    service = DocumentService(settings)
    # Admins see all jobs, others see their own
    user_id = None if str(getattr(current_user, 'role', '')).lower() in ["admin", "administrator"] else str(current_user.id)
    jobs = await service.list_jobs(user_id=user_id, status=status, limit=limit)
    return {
        "jobs": [
            {
                "id": str(j.id),
                "document_id": j.document_id,
                "filename": j.filename,
                "status": j.status.value if hasattr(j.status, 'value') else str(j.status).replace('JobStatus.', '').lower(),
                "current_step": j.current_step.value if hasattr(j.current_step, 'value') else str(j.current_step).replace('JobStep.', '').lower(),
                "completed_steps": j.completed_steps,
                "failed_step": j.failed_step,
                "error_message": j.error_message,
                "pages_extracted": j.pages_extracted,
                "chunks_created": j.chunks_created,
                "embeddings_created": j.embeddings_created,
                "kg_nodes_created": j.kg_nodes_created,
                "kg_relations_created": j.kg_relations_created,
                "elapsed_seconds": j.elapsed_seconds,
                "started_at": j.started_at.isoformat() if j.started_at else None,
                "completed_at": j.completed_at.isoformat() if j.completed_at else None,
                "created_at": j.created_at.isoformat(),
            }
            for j in jobs
        ]
    }


@router.get("/jobs/{job_id}")
async def get_job_status(
    job_id: str,
    settings: SettingsDep,
    current_user: CurrentUserDep,
):
    """Get status of a specific processing job."""
    service = DocumentService(settings)
    job = await service.get_job_status(job_id)
    if not job:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "id": str(job.id),
        "document_id": job.document_id,
        "filename": job.filename,
        "status": job.status.value if hasattr(job.status, 'value') else str(job.status).replace('JobStatus.', '').lower(),
        "current_step": job.current_step.value if hasattr(job.current_step, 'value') else str(job.current_step).replace('JobStep.', '').lower(),
        "completed_steps": job.completed_steps,
        "failed_step": job.failed_step,
        "error_message": job.error_message,
        "pages_extracted": job.pages_extracted,
        "chunks_created": job.chunks_created,
        "embeddings_created": job.embeddings_created,
        "kg_nodes_created": job.kg_nodes_created,
        "kg_relations_created": job.kg_relations_created,
        "elapsed_seconds": job.elapsed_seconds,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }


@router.post("/upload-async", status_code=202)
async def upload_document_async(
    settings: SettingsDep,
    chroma_indexer: ChromaIndexerDep,
    kg_builder: KGBuilderDep,
    current_user: CurrentUserDep,
    file: UploadFile = File(...),
    document_type: DocumentType = Form(default=DocumentType.GENERAL),
    category: str = Form(default="GENERAL"),
):
    """Upload a document and return immediately. Processing runs in background.
    
    Returns a job_id to poll for processing status.
    """
    if str(getattr(current_user, 'role', '')).lower() not in ["admin", "administrator"]:
        raise HTTPException(status_code=403, detail="Only administrators can manage the Global Knowledge Base")
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")
    
    service = DocumentService(settings, chroma_indexer=chroma_indexer, kg_builder=kg_builder)
    
    try:
        job = await service.upload_and_queue(
            file=file.file,
            filename=file.filename,
            content_type=file.content_type or "application/pdf",
            document_type=document_type,
            category=category,
            owner_id=str(current_user.id),
        )
    except DocumentUploadError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc
    
    return {
        "job_id": str(job.id),
        "document_id": job.document_id,
        "filename": job.filename,
        "status": str(job.status),
        "message": f"Document queued for processing. Poll /api/v1/documents/jobs/{job.id} for status."
    }


@router.get("/{document_id}", response_model=DocumentDetail)
async def get_document(
    document_id: str,
    settings: SettingsDep,
    current_user: CurrentUserDep,
):
    """Get detailed information about a specific document.

    Includes extracted page content with metadata.
    """
    service = DocumentService(settings)
    try:
        doc = await service.get_document(document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc

    return DocumentDetail(
        id=str(doc.id),
        filename=doc.filename,
        document_type=doc.document_type,
        status=doc.status,
        total_pages=doc.total_pages,
        total_chunks=doc.total_chunks,
        file_size_bytes=doc.file_size_bytes,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        pages=[
            {
                "page_number": p.page_number,
                "text": p.text[:500] + "..." if len(p.text) > 500 else p.text,
                "sections": p.sections,
                "char_count": p.char_count,
            }
            for p in doc.pages
        ],
        metadata=doc.metadata,
        error_message=doc.error_message,
    )


@router.delete("/{document_id}", status_code=200)
async def delete_document(
    document_id: str,
    settings: SettingsDep,
    chroma_indexer: ChromaIndexerDep,
    kg_builder: KGBuilderDep,
    current_user: CurrentUserDep,
):
    """Delete a document, its file, its vector embeddings, and its KG entities."""
    if current_user.role != "Administrator":
        raise HTTPException(status_code=403, detail="Only administrators can manage the Global Knowledge Base")
    service = DocumentService(settings, chroma_indexer=chroma_indexer, kg_builder=kg_builder)
    try:
        await service.delete_document(document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc

    return {"message": f"Document {document_id} deleted successfully."}


