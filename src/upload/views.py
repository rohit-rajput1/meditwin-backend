import os
from fastapi import APIRouter, UploadFile, Form, File, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from .dependency import limiter, get_report_type, allowed_file, openai_client
from .manager import file_upload, analyze_report
from .schema import FileUploadResponse, AnalysisResponse
from database.gets import get_db
from database.models.report import Report
from datetime import datetime, timezone
from src.auth.dependency import get_current_user
from sqlalchemy import insert, select
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
    """
    Upload and process a medical document (prescription or blood report)
    """
    try:
        # Validate report type
        await get_report_type(db, report_type_id)

        # Validate file type
        if not allowed_file(report_file.filename):
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Allowed: PDF, JPEG, JPG, PNG"
            )

        # Generate file UUID
        file_id = uuid4()

        # Extract report name (filename without extension)
        report_name = os.path.splitext(report_file.filename)[0]

        # Insert into Report table
        stmt = insert(Report).values(
            report_id=file_id,
            user_id=current_user.user_id,
            report_type_id=report_type_id,
            report_name=report_name,
            status="processing",
            uploaded_at=datetime.now(timezone.utc)
        )

        await db.execute(stmt)
        await db.commit()

        # Background processing
        await file_upload(
            report_file,
            file_id=file_id,
            background=True,
            background_tasks=background_tasks
        )

        return FileUploadResponse(
            file_id=file_id,
            report_name=report_name,
            status="processing",
            message=f"File '{report_file.filename}' uploaded successfully. Processing in background.",
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@upload_router.get("/status/{file_id}")
async def get_report_status(
    file_id: str, 
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Check the processing status of an uploaded report"""
    try:
        result = await db.execute(
            select(Report).where(
                Report.report_id == file_id,
                Report.user_id == current_user.user_id
            )
        )
        report = result.scalar_one_or_none()
        
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        # Get text preview from summary if available
        text_preview = None
        text_length = 0
        if report.summary and isinstance(report.summary, dict):
            text_preview = report.summary.get("preview", "")
            text_length = report.summary.get("text_length", 0)
        
        return {
            "file_id": file_id,
            "status": report.status,
            "uploaded_at": report.uploaded_at,
            "text_length": text_length,
            "text_preview": text_preview[:500] if text_preview else None,
            "error": report.insights.get("error") if report.status == "failed" else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch status: {str(e)}")

@upload_router.post("/analyze/{file_id}", response_model=AnalysisResponse)
async def analyze_report_file(
    file_id: str, 
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Analyze a processed report and extract structured medical information.
    Returns summary, key findings, and recommendations.
    """
    try:
        # Verify ownership
        result = await db.execute(
            select(Report).where(
                Report.report_id == file_id,
                Report.user_id == current_user.user_id
            )
        )
        report = result.scalar_one_or_none()
        
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        analysis = await analyze_report(file_id, db, openai_client)
        return analysis
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")