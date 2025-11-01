from fastapi import UploadFile, BackgroundTasks, HTTPException
from .process import process_upload
from .utils import create_file_id
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models.report import Report
from database.models.report_type import ReportType
from .dependency import pinecone_index
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
    """
    Analyze a report using the text stored in Pinecone metadata.
    Returns structured AI output: summary, key_findings, insights, recommendations.
    """

    # --- 1. Fetch report from Postgres ---
    result = await db.execute(select(Report).where(Report.report_id == file_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    namespace = report.insights.get("namespace")
    if not namespace:
        raise HTTPException(status_code=400, detail="Pinecone namespace not found for this report")

    # --- 2. Fetch vector from Pinecone ---
    try:
        fetched = pinecone_index.fetch(ids=[str(file_id)], namespace=namespace)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch from Pinecone: {e}")

    vector_data = fetched.vectors.get(str(file_id))
    if not vector_data or not hasattr(vector_data, "metadata") or "text" not in vector_data.metadata:
        raise HTTPException(status_code=400, detail="Text not found in Pinecone metadata")

    document_text = vector_data.metadata["text"]
    if not document_text.strip():
        raise HTTPException(status_code=400, detail="Extracted text is empty")

    # --- 3. Fetch report type ---
    result = await db.execute(select(ReportType).where(ReportType.report_type_id == report.report_type_id))
    report_type = result.scalar_one_or_none()
    if not report_type:
        raise HTTPException(status_code=404, detail="Report type not found")

    prompt_template = PROMPTS.get(report_type.name)
    if not prompt_template:
        raise HTTPException(status_code=400, detail=f"No analysis prompt found for {report_type.name}")

    # --- 4. Prepare AI prompt to always return JSON ---
    prompt_template += (
        "\n\nReturn the output strictly as valid JSON with the following keys: "
        "summary (string), key_findings (dictionary), insights (string), recommendations (list of strings). "
        "If the document does not contain extractable information, return empty fields. Example:\n"
        "{\n"
        '  "summary": "",\n'
        '  "key_findings": {},\n'
        '  "insights": "",\n'
        '  "recommendations": []\n'
        "}"
    )

    # --- 5. Call OpenAI ---
    try:
        completion = openai_client.responses.create(
            model="gpt-4.1",
            input=f"{prompt_template}\n\nDocument Text:\n{document_text[:4000]}"  # truncate for token limits
        )

        raw_text = completion.output[0].content[0].text if completion.output else "{}"

        try:
            analysis = json.loads(raw_text)
        except json.JSONDecodeError:
            # Fallback: empty structured response
            analysis = {
                "summary": "",
                "key_findings": {},
                "insights": "",
                "recommendations": []
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI analysis failed: {e}")

    # --- 6. Update report in Postgres ---
    report.summary = analysis.get("summary", "")
    report.key_findings = analysis.get("key_findings", {})
    report.insights.update(analysis)
    report.recommendations = analysis.get("recommendations", [])

    db.add(report)
    await db.commit()
    await db.refresh(report)

    return analysis