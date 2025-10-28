from fastapi import APIRouter, UploadFile, Form, File, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from .dependency import limiter, get_report_type, allowed_file, openai_client
from .manager import file_upload, analyze_report
from .schema import FileUploadResponse, AnalysisResponse
from database.gets import get_db
from database.models.report import Report
from datetime import datetime, timezone
from src.auth.dependency import get_current_user
from sqlalchemy import insert
from uuid import uuid4

upload_router = APIRouter(tags=["Upload"])

@upload_router.post("/upload-file", response_model=FileUploadResponse)
@limiter.limit("5/minute")
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
        file_id = uuid4()

        # Insert report entry in Postgres
        stmt = insert(Report).values(
            report_id=file_id,
            user_id=current_user.user_id,
            report_type_id=report_type_id,
            status="processing",
            uploaded_at=datetime.now(timezone.utc)
        )
        await db.execute(stmt)
        await db.commit()

        # Trigger background processing - PASS file_id
        await file_upload(
            report_file, 
            file_id=file_id,  # Pass the same file_id created above
            background=True, 
            background_tasks=background_tasks
        )

        return FileUploadResponse(
            file_id=file_id,
            status="processing",
            message=f"{report_file.filename} upload initiated. Processing in background."
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
@upload_router.post("/{file_id}", response_model=AnalysisResponse)
async def analyze_report_file(file_id: str, db: AsyncSession = Depends(get_db)):
    """
    Analyze a report based on its report_type and generate:
    summary, key findings, insights, and recommendations.
    """
    analysis = await analyze_report(file_id, db, openai_client)
    return analysis