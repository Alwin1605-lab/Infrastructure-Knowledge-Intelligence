"""MongoDB ODM models using Beanie.

Defines the document models stored in MongoDB:
    - Document: Infrastructure document metadata (PDF reports, manuals, etc.)
    - ChatHistory: Conversation history with structured responses.
    - Report: Generated maintenance reports.
"""

from app.models.document import Document
from app.models.chat import ChatHistory
from app.models.report import Report

__all__ = ["Document", "ChatHistory", "Report"]

# All Beanie document models — used by db/connection.py for initialization
ALL_MODELS = [Document, ChatHistory, Report]
