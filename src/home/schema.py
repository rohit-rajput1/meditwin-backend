from pydantic import BaseModel
from uuid import UUID
from typing import List, Optional, Union
from datetime import datetime

class ReportTypeResponse(BaseModel):
    report_type_id: UUID
    name: str
    
    class Config:
        from_attributes = True

class StatusItem(BaseModel):
    status: str

class ReportListItem(BaseModel):
    report_id: UUID
    report_name: Optional[str]
    report_type: str
    summary: Optional[Union[dict, str]]
    created_at: datetime 
    status: Optional[str] = None
    
    class Config:
        from_attributes = True

class PaginatedReportList(BaseModel):
    page: int
    limit: int
    total: int
    total_pages: int
    data: List[ReportListItem]

class ReportNameUpdateRequest(BaseModel):
    report_id: UUID
    report_name: str

class ReportNameUpdateResponse(BaseModel):
    report_id: UUID
    report_name: str
    
    class Config:
        from_attributes = True

class ReportDeleteRequest(BaseModel):
    report_id: UUID

class ReportDeleteResponse(BaseModel):
    report_id: UUID
    report_name: Optional[str] = None
    message: str

    class Config:
        from_attributes = True