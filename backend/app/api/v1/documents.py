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
    if current_user.role != "Administrator":
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
