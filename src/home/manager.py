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
