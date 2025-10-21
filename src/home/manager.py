import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database.models.report_type import ReportType
from typing import List,Tuple
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError
from database.models import *

async def get_all_report_types(db: AsyncSession) -> ReportType:
    """
    Fetch all report types from the database.
    """
    try:
        result = await db.execute(select(ReportType))
        report_types = result.scalars().all()
        return report_types
    except SQLAlchemyError as e:
        raise Exception(f"Database error while fetching report types: {str(e)}")
    except Exception as e:
        raise Exception(f"Unexpected error while fetching report types: {str(e)}")

async def create_report(
    db: AsyncSession, 
    report_type_id: uuid.UUID, 
    user_id: uuid.UUID
) -> Tuple[Report, ReportType]:
    """
    Creates a new report linked to a report type and user.
    """
    try:
        # 1. Check if report type exists
        result = await db.execute(select(ReportType).where(ReportType.report_type_id == report_type_id))
        report_type = result.scalars().first()
        if not report_type:
            raise ValueError("Report type not found")

        # 2. Create new report
        new_report = Report(
            report_id=uuid.uuid4(),
            report_type_id=report_type.report_type_id,
            user_id=user_id
        )
        db.add(new_report)
        await db.commit()
        await db.refresh(new_report)

        return new_report, report_type

    except SQLAlchemyError as e:
        await db.rollback()
        raise Exception(f"Database error: {str(e)}")