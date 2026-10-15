"""Notifications API endpoints."""
from fastapi import APIRouter, Query
from pydantic import BaseModel
from app.api.deps import CurrentUserDep
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])

class NotificationResponse(BaseModel):
    id: str
    title: str
    message: str
    notification_type: str
    is_read: bool
    link: str | None
    created_at: str

@router.get("")
async def list_notifications(
    current_user: CurrentUserDep,
    unread_only: bool = Query(default=False),
    limit: int = Query(default=20, le=50),
):
    """List notifications for current user."""
    svc = NotificationService()
    notifications = await svc.list_for_user(
        user_id=str(current_user.id),
        limit=limit,
        unread_only=unread_only,
    )
    unread_count = await svc.unread_count(str(current_user.id))
    return {
        "notifications": [
            {
                "id": str(n.id),
                "title": n.title,
                "message": n.message,
                "notification_type": str(n.notification_type),
                "is_read": n.is_read,
                "link": n.link,
                "created_at": n.created_at.isoformat(),
            }
            for n in notifications
        ],
        "unread_count": unread_count,
    }

@router.put("/{notification_id}/read")
async def mark_read(notification_id: str, current_user: CurrentUserDep):
    svc = NotificationService()
    await svc.mark_read(notification_id, str(current_user.id))
    return {"ok": True}

@router.put("/read-all")
async def mark_all_read(current_user: CurrentUserDep):
    svc = NotificationService()
    count = await svc.mark_all_read(str(current_user.id))
    return {"marked_read": count}
