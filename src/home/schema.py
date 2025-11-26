from pydantic import BaseModel
from uuid import UUID
from typing import List

class ReportTypeResponse(BaseModel):
    report_type_id: UUID
    name: str

    class Config:
        orm_mode = True
