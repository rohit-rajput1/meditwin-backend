from pydantic import BaseModel
from uuid import UUID

class FileUploadResponse(BaseModel):
    file_id: UUID
    status: str
    message: str