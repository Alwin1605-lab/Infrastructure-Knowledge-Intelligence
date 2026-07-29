from fastapi import APIRouter, HTTPException, Query, status
from typing import Optional

from app.api.deps import CurrentUserDep, SettingsDep
from app.models.workspace import Workspace
from app.models.activity import ActivityLog
from app.schemas.workspace import WorkspaceCreate, WorkspaceResponse, WorkspaceListResponse

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    workspace_in: WorkspaceCreate,
    current_user: CurrentUserDep,
):
    """Create a new workspace for the user's organization."""
    if current_user.is_guest:
        raise HTTPException(status_code=403, detail="Guest users cannot create workspaces.")

    workspace = Workspace(
        organization_id=current_user.organization_id,
        owner_id=str(current_user.id),
        name=workspace_in.name,
        building_type=workspace_in.building_type,
        location=workspace_in.location,
        description=workspace_in.description,
    )
    await workspace.insert()
    
    # Log activity
    await ActivityLog(
        user_id=str(current_user.id),
        organization_id=current_user.organization_id,
        workspace_id=str(workspace.id),
        action="workspace_created",
        details=f"Created workspace '{workspace.name}'"
    ).insert()

    return WorkspaceResponse(
        id=str(workspace.id),
        name=workspace.name,
        building_type=workspace.building_type,
        location=workspace.location,
        description=workspace.description,
        status=workspace.status,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at
    )


@router.get("", response_model=WorkspaceListResponse)
async def list_workspaces(
    current_user: CurrentUserDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """List all workspaces in the user's organization."""
    total = await Workspace.find({"organization_id": current_user.organization_id}).count()
    workspaces = await Workspace.find({"organization_id": current_user.organization_id}).skip(skip).limit(limit).to_list()
    
    return WorkspaceListResponse(
        workspaces=[
            WorkspaceResponse(
                id=str(w.id),
                name=w.name,
                building_type=w.building_type,
                location=w.location,
                description=w.description,
                status=w.status,
                created_at=w.created_at,
                updated_at=w.updated_at
            ) for w in workspaces
        ],
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: str,
    current_user: CurrentUserDep,
):
    """Get workspace details."""
    workspace = await Workspace.get(workspace_id)
    if not workspace or workspace.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Workspace not found")
        
    return WorkspaceResponse(
        id=str(workspace.id),
        name=workspace.name,
        building_type=workspace.building_type,
        location=workspace.location,
        description=workspace.description,
        status=workspace.status,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at
    )


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: str,
    current_user: CurrentUserDep,
):
    """Delete a workspace."""
    workspace = await Workspace.get(workspace_id)
    if not workspace or workspace.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Workspace not found")
        
    if workspace.owner_id != str(current_user.id) and current_user.role != "Administrator":
        raise HTTPException(status_code=403, detail="Not authorized to delete this workspace")
        
    await workspace.delete()
    
    # Log activity
    await ActivityLog(
        user_id=str(current_user.id),
        organization_id=current_user.organization_id,
        workspace_id=workspace_id,
        action="workspace_deleted",
        details=f"Deleted workspace '{workspace.name}'"
    ).insert()
