from fastapi import APIRouter, Query

from app.api.deps import CurrentUserDep
from app.models.activity import ActivityLog
from app.schemas.activity import ActivityListResponse, ActivityResponse

router = APIRouter(prefix="/activity", tags=["Activity"])

@router.get("", response_model=ActivityListResponse)
async def list_activity(
    current_user: CurrentUserDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
):
    """List recent activity for the user's organization."""
    total = await ActivityLog.find({"organization_id": current_user.organization_id}).count()
    activities = await ActivityLog.find(
        {"organization_id": current_user.organization_id}
    ).sort("-timestamp").skip(skip).limit(limit).to_list()
    
    return ActivityListResponse(
        activities=[
            ActivityResponse(
                id=str(a.id),
                user_id=a.user_id,
                workspace_id=a.workspace_id,
                action=a.action,
                details=a.details,
                timestamp=a.timestamp
            ) for a in activities
        ],
        total=total
    )
