from pydantic import BaseModel
from uuid import UUID
from typing import Dict, Any

class DashboardCreateRequest(BaseModel):
    file_id: UUID

class DashboardResponse(BaseModel):
    dashboard_id: UUID
    dashboard_type: str
    data: Dict[str, Any]
