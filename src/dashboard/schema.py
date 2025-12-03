from pydantic import BaseModel, Field
from uuid import UUID
from typing import Dict, Any, List
from datetime import datetime


class DashboardCreateRequest(BaseModel):
    file_id: UUID

    class Config:
        from_attributes = True


class DashboardResponse(BaseModel):
    dashboard_id: UUID
    dashboard_type: str
    user_id: UUID
    report_id: UUID
    created_at: datetime

    topBar: Dict[str, Any] = Field(default_factory=dict)
    middleSection: Dict[str, Any] = Field(default_factory=dict)
    recommendations: List[str] = Field(default_factory=list)
    criticalInsights: List[str] = Field(default_factory=list)

    class Config:
        from_attributes = True

    @classmethod
    def from_dashboard_model(cls, dashboard):
        return cls(
            dashboard_id=dashboard.dashboard_id,
            dashboard_type=dashboard.dashboard_type,
            user_id=dashboard.user_id,
            report_id=dashboard.report_id,
            created_at=dashboard.created_at,
            topBar=dashboard.top_bar or {},
            middleSection=dashboard.middle_section or {},
            recommendations=dashboard.recommendations or [],
            criticalInsights=dashboard.critical_insights or [],
        )
