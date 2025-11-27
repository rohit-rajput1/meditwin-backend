from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from database.gets import get_db
from src.auth.dependency import get_current_user
from .manager import create_dashboard
from .schema import DashboardResponse, DashboardCreateRequest

dashboard_router = APIRouter(tags=["Dashboard"])

@dashboard_router.post("/create", response_model=DashboardResponse)
async def create_dashboard_api(
    payload: DashboardCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    try:
        result = await create_dashboard(payload.file_id, db)

        return DashboardResponse(
            dashboard_id=result["dashboard_id"],
            dashboard_type=result["dashboard_type"],
            data=result["data"],
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Dashboard creation failed: {str(e)}")
