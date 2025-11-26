from typing import List
from fastapi import APIRouter,Depends,status,Request,HTTPException
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from . import manager
from . import schema
from database.gets import get_db

report_router = APIRouter(tags=["Report"])

@report_router.get(
    "/report_types",
    response_model=List[schema.ReportTypeResponse],
    status_code=status.HTTP_200_OK
)
async def get_report_types(db: AsyncSession = Depends(get_db)):
    """
    Get the list of all report types with their IDs and names.
    """
    try:
        report_types = await manager.get_all_report_types(db)
        return report_types
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error occurred: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error occurred: {str(e)}"
        )
