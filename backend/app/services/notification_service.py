"""Notification Service — creates and retrieves user notifications."""

from datetime import datetime, timezone
from typing import Optional

from app.models.notification import Notification, NotificationType
from app.core.logging import get_logger

logger = get_logger(__name__)


class NotificationService:
    """Manages user notifications."""
    
    async def create(
        self,
        user_id: str,
        title: str,
        message: str,
        notification_type: NotificationType = NotificationType.SYSTEM,
        link: Optional[str] = None,
    ) -> Notification:
        """Create a new notification for a user."""
        notif = Notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            link=link,
        )
        await notif.insert()
        logger.info("notification_created", user_id=user_id, type=notification_type)
        return notif
    
    async def list_for_user(
        self,
        user_id: str,
        limit: int = 20,
        unread_only: bool = False,
    ) -> list[Notification]:
        """Get notifications for a user."""
        filters = {"user_id": user_id}
        if unread_only:
            filters["is_read"] = False
        return await Notification.find(filters).sort("-created_at").limit(limit).to_list()
    
    async def mark_read(self, notification_id: str, user_id: str) -> bool:
        """Mark a specific notification as read."""
        notif = await Notification.get(notification_id)
        if notif and notif.user_id == user_id:
            notif.is_read = True
            notif.read_at = datetime.now(timezone.utc)
            await notif.save()
            return True
        return False
    
    async def mark_all_read(self, user_id: str) -> int:
        """Mark all notifications as read for a user."""
        unread = await Notification.find({"user_id": user_id, "is_read": False}).to_list()
        count = 0
        for notif in unread:
            notif.is_read = True
            notif.read_at = datetime.now(timezone.utc)
            await notif.save()
            count += 1
        return count
    
    async def unread_count(self, user_id: str) -> int:
        """Get count of unread notifications."""
        return await Notification.find({"user_id": user_id, "is_read": False}).count()
