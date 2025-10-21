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

@report_router.post(
    "/get_report_id",
    response_model=schema.CreateReportResponse,
    status_code=status.HTTP_201_CREATED
)
async def get_report_id(
    request: schema.CreateReportRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new report for a given report_type_id and user_id.
    Returns the new report_id, report_type_id, and name of the report type.
    """
    try:
        new_report, report_type = await manager.create_report(
            db,
            report_type_id=request.report_type_id,
            user_id=request.user_id
        )
        return schema.CreateReportResponse(
            report_id=new_report.report_id,
            report_type_id=report_type.report_type_id,
            name=report_type.name
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))