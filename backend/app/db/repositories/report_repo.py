"""Report repository — CRUD operations for generated reports."""

from typing import Optional

from beanie import PydanticObjectId

from app.core.logging import get_logger
from app.models.report import Report, ReportStatus

logger = get_logger(__name__)


class ReportRepository:
    """Repository for Report CRUD operations."""

    @staticmethod
    async def create(report: Report) -> Report:
        """Insert a new report."""
        await report.insert()
        logger.info("report_created", report_id=str(report.id), title=report.title)
        return report

    @staticmethod
    async def get_by_id(report_id: str) -> Optional[Report]:
        """Retrieve a report by ID."""
        return await Report.get(PydanticObjectId(report_id))

    @staticmethod
    async def get_all(skip: int = 0, limit: int = 50) -> list[Report]:
        """Retrieve all reports, newest first."""
        return await Report.find().sort(-Report.created_at).skip(skip).limit(limit).to_list()

    @staticmethod
    async def update(report: Report) -> Report:
        """Update an existing report."""
        await report.save()
        return report

    @staticmethod
    async def delete(report_id: str) -> bool:
        """Delete a report by ID."""
        report = await Report.get(PydanticObjectId(report_id))
        if report is None:
            return False
        await report.delete()
        logger.info("report_deleted", report_id=report_id)
        return True
