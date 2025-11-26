from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from uuid import UUID

class FileUploadResponse(BaseModel):
    file_id: UUID
    status: str
    message: str

class AnalysisRequest(BaseModel):
    file_id: UUID

class AnalysisResponse(BaseModel):
    summary: str
    key_findings: Dict[str, Any]
    insights: Optional[str] = None
    recommendations: List[str]