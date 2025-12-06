from typing import List
from fastapi import APIRouter,Depends,status,Request,HTTPException
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from database.models import *
from sqlalchemy.future import select
from . import manager
from . import schema
from database.gets import get_db
from src.auth.dependency import get_current_user

report_router = APIRouter(tags=["Report"])

@report_router.get(
    "/report_types",
    response_model=List[schema.ReportTypeResponse],
    status_code=status.HTTP_200_OK
)
async def get_report_types(db: AsyncSession = Depends(get_db),current_user=Depends(get_current_user)):
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

@report_router.get("/report-status", response_model=list[schema.StatusItem])
async def get_report_status(db: AsyncSession = Depends(get_db),current_user=Depends(get_current_user)):
    try:
        query = select(Report.status).distinct()
        result = await db.execute(query)
        statuses = [row[0] for row in result.fetchall() if row[0]]

        return [schema.StatusItem(status=s) for s in statuses]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected Error: {str(e)}")


@report_router.get(
    "/report-list",
    response_model=schema.PaginatedReportList
)
async def get_report_list(
    search: str | None = None,
    sort: str | None = "desc",
    page: int = 1,
    limit: int = 10,
    report_type_name: str | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    try:
        reports, total = await manager.get_all_reports(
            db, search, sort, page, limit, report_type_name, status
        )

        total_pages = max((total + limit - 1) // limit, 1)

        # Clean summary (fix string problem)
        def clean_summary(value):
            if isinstance(value, dict):
                return value
            if isinstance(value, str):
                return {"text": value}  # fallback for inconsistent data
            return None

        response_data = [
            schema.ReportListItem(
                report_id=r.report_id,
                report_name=r.report_name,
                report_type=r.report_type.name,
                summary=clean_summary(r.summary),
                created_at=r.uploaded_at
            )
            for r in reports
        ]

        return schema.PaginatedReportList(
            page=page,
            limit=limit,
            total=total,
            total_pages=total_pages,
            data=response_data
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@report_router.put(
    "/update-name",
    response_model=schema.ReportNameUpdateResponse,
    status_code=status.HTTP_200_OK
)
async def update_report_name(
    payload: schema.ReportNameUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    try:
        updated = await manager.update_report_name(
            db,
            report_id=payload.report_id,
            new_name=payload.report_name
        )

        if not updated:
            raise HTTPException(
                status_code=404,
                detail="Report not found"
            )

        return updated

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )

@report_router.delete(
    "/delete",
    response_model=schema.ReportDeleteResponse,
    status_code=status.HTTP_200_OK
)
async def delete_report(
    payload: schema.ReportDeleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    try:
        result = await manager.delete_report(db, payload.report_id)

        if not result:
            raise HTTPException(
                status_code=404,
                detail="Report not found"
            )

        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )