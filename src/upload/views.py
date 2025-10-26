from fastapi import APIRouter, UploadFile, Form, File, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from .dependency import limiter, get_report_type, allowed_file
from .manager import file_upload
from .schema import FileUploadResponse
from database.gets import get_db
from src.auth.dependency import get_current_user

upload_router = APIRouter(tags=["Upload"])

@upload_router.post("/upload-file", response_model=FileUploadResponse)
@limiter.limit("1/minute")
async def upload_file(
    request: Request,
    background_tasks: BackgroundTasks,
    report_type_id: str = Form(...),
    report_file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    # Validate report type
    await get_report_type(db, report_type_id)

    # Validate file type
    if not allowed_file(report_file.filename):
        raise HTTPException(status_code=400, detail="Invalid File Type")

    try:
        file_id = await file_upload(report_file, background=True, background_tasks=background_tasks)
        return FileUploadResponse(
            file_id=file_id,
            status="success",
            message=f"{report_file.filename} upload initiated. Embedding will be processed in the background"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))