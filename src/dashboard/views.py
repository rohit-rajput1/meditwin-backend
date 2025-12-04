from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database.gets import get_db
from src.auth.dependency import get_current_user
from .manager import create_dashboard,get_dashboard_by_file_id
from .schema import DashboardResponse, DashboardCreateRequest
from uuid import UUID

dashboard_router = APIRouter(tags=["Dashboard"])

@dashboard_router.post("/create", response_model=DashboardResponse)
async def create_dashboard_api(
    payload: DashboardCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        dashboard = await create_dashboard(payload.file_id, db)
        return DashboardResponse.from_dashboard_model(dashboard)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Dashboard creation failed: {str(e)}")

@dashboard_router.get("/{file_id}", response_model=DashboardResponse)
async def get_dashboard_api(
    file_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        dashboard = await get_dashboard_by_file_id(file_id, db)
        return DashboardResponse.from_dashboard_model(dashboard)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Dashboard fetch failed: {str(e)}")
