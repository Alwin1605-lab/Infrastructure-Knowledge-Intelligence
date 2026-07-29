from typing import Optional
from fastapi import APIRouter, File, Form, UploadFile, HTTPException, Query, status

from app.api.deps import SettingsDep, ChromaIndexerDep, KGBuilderDep, CurrentUserDep
from app.models.workspace import Workspace
from app.models.workspace_document import WorkspaceDocument
from app.models.activity import ActivityLog
from app.services.document_service import DocumentService
from app.core.exceptions import DocumentUploadError, DocumentExtractionError
from app.schemas.document import DocumentUploadResponse, DocumentSummary, DocumentDetail, DocumentListResponse

router = APIRouter(prefix="/workspaces/{workspace_id}/documents", tags=["Workspace Documents"])


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_workspace_document(
    workspace_id: str,
    settings: SettingsDep,
    chroma_indexer: ChromaIndexerDep,
    kg_builder: KGBuilderDep,
    current_user: CurrentUserDep,
    file: UploadFile = File(..., description="PDF file to upload."),
    document_type: str = Form("General"),
):
    """Upload a document to a specific workspace."""
    if current_user.is_guest:
        raise HTTPException(status_code=403, detail="Guest users cannot upload documents.")
        
    workspace = await Workspace.get(workspace_id)
    if not workspace or workspace.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Workspace not found")

    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")

    service = DocumentService(settings, chroma_indexer=chroma_indexer, kg_builder=kg_builder)

    try:
        # Note: DocumentService needs to be adapted to handle workspace_id in its metadata
        document = await service.upload_document(
            file=file.file,
            filename=file.filename,
            content_type=file.content_type or "application/pdf",
            document_type=document_type,
            workspace_id=workspace_id,
            owner_id=str(current_user.id)
        )
    except DocumentUploadError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc
    except DocumentExtractionError as exc:
        raise HTTPException(status_code=422, detail=exc.message) from exc
        
    # Log activity
    await ActivityLog(
        user_id=str(current_user.id),
        organization_id=current_user.organization_id,
        workspace_id=workspace_id,
        action="document_uploaded",
        details=f"Uploaded document '{file.filename}'"
    ).insert()

    return DocumentUploadResponse(
        id=str(document.id),
        filename=document.filename,
        file_size_bytes=document.file_size_bytes,
        document_type=document.document_type,
        status=document.status,
        message=f"Document uploaded successfully to workspace.",
        created_at=document.created_at,
    )
