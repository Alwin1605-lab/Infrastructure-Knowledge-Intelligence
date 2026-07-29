"""MongoDB ODM models using Beanie.

Defines the document models stored in MongoDB:
    - Document: Infrastructure document metadata (PDF reports, manuals, etc.)
    - ChatHistory: Conversation history with structured responses.
    - Report: Generated maintenance reports.
    - Organization: User organization/tenant.
    - User: Authenticated user profile.
    - Workspace: Project/workspace container.
    - WorkspaceDocument: Documents scoped to a specific workspace.
    - ActivityLog: User activity tracking.
    - RefreshToken: JWT refresh token persistence.
    - UserPreferences: User settings.
    - Notification: System notifications.
"""

from app.models.document import Document
from app.models.chat import ChatHistory
from app.models.report import Report
from app.models.organization import Organization
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_document import WorkspaceDocument
from app.models.activity import ActivityLog
from app.models.refresh_token import RefreshToken
from app.models.user_preferences import UserPreferences
from app.models.notification import Notification


__all__ = [
    "Document", 
    "ChatHistory", 
    "Report",
    "Organization",
    "User",
    "Workspace",
    "WorkspaceDocument",
    "ActivityLog",
    "RefreshToken",
    "UserPreferences",
    "Notification"
]

# All Beanie document models — used by db/connection.py for initialization
ALL_MODELS = [
    Document, 
    ChatHistory, 
    Report,
    Organization,
    User,
    Workspace,
    WorkspaceDocument,
    ActivityLog,
    RefreshToken,
    UserPreferences,
    Notification
]
