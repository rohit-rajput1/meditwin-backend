from fastapi import UploadFile, BackgroundTasks, HTTPException
from .process import process_upload
from .utils import create_file_id
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models.report import Report
from database.models.report_type import ReportType
from .prompt import PROMPTS
import json
from uuid import UUID

async def file_upload(
    file: UploadFile, 
    file_id: UUID,  # Make file_id required
    background=False, 
    background_tasks: BackgroundTasks = None
):
    """
    Entry point for API and background processing.
    Embeddings are only stored in Pinecone, not Postgres.
    """
    try:
        if background and background_tasks:
            content = await file.read()
            await file.seek(0)
            # Pass file_id to background task
            background_tasks.add_task(process_upload, file, file_id, content)
            return file_id
        else:
            return await process_upload(file, file_id)
    except Exception as e:
        raise RuntimeError(f"File upload failed: {e}")
    
async def analyze_report(file_id: str, db: AsyncSession, openai_client):
    # Fetch report
    result = await db.execute(select(Report).where(Report.report_id == file_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Fetch report type
    result = await db.execute(select(ReportType).where(ReportType.report_type_id == report.report_type_id))
    report_type = result.scalar_one_or_none()
    if not report_type:
        raise HTTPException(status_code=404, detail="Report type not found")

    prompt_template = PROMPTS.get(report_type.name)
    if not prompt_template:
        raise HTTPException(status_code=400, detail=f"No analysis prompt found for {report_type.name}")

    # Placeholder for document content extraction
    document_text = f"Analyze the {report_type.name}."

    # Call OpenAI for structured analysis
    completion = openai_client.responses.create(
        model="gpt-4.1",
        input=f"{prompt_template}\n\nDocument:\n{document_text}"
    )

    try:
        content = completion.output[0].content[0].text
        analysis = json.loads(content)
    except Exception:
        raise HTTPException(status_code=500, detail="Invalid or unstructured AI response")

    # Save analysis results in DB
    report.summary = analysis.get("summary")
    report.key_findings = analysis.get("key_findings")
    report.insights = analysis.get("insights")
    report.recommendations = analysis.get("recommendations")

    db.add(report)
    await db.commit()
    await db.refresh(report)

    return analysis