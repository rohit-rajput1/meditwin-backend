from fastapi import UploadFile, BackgroundTasks, HTTPException
from .process import process_upload
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models.report import Report
from database.models.report_type import ReportType
from .dependency import pinecone_index
from .prompt import PROMPTS
import json
import re
from uuid import UUID
from datetime import datetime, timezone

async def file_upload(
    file: UploadFile,
    file_id: UUID,
    background=False,
    background_tasks: BackgroundTasks = None
):
    """Handles file upload + background processing."""
    try:
        if background and background_tasks:
            content = await file.read()
            await file.seek(0)
            background_tasks.add_task(process_upload, file, file_id, content)
            return file_id
        else:
            return await process_upload(file, file_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")

def extract_json_from_text(text: str) -> dict:
    """Extract clean JSON from LLM output."""
    try:
        text = text.strip()
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            text = json_match.group(1)
        text = re.sub(r'^```json\s*|\s*```$', '', text, flags=re.MULTILINE).strip()
        return json.loads(text)
    except json.JSONDecodeError:
        raise ValueError("Failed to parse AI response as valid JSON")

async def analyze_report(file_id: str, db: AsyncSession, openai_client):
    """Analyze extracted text using OpenAI and update DB."""
    
    try:
        # Fetch report
        result = await db.execute(select(Report).where(Report.report_id == file_id))
        report = result.scalar_one_or_none()
        
        if not report:
            raise HTTPException(404, "Report not found")
        
        if report.status == "processing":
            raise HTTPException(400, "Report is still being processed. Try again shortly.")
        
        if report.status == "failed":
            raise HTTPException(400, f"Report processing failed: {report.insights.get('error')}")
        
        namespace = report.insights.get("namespace")
        if not namespace:
            raise HTTPException(400, "Document text not found. Re-upload file.")
        
        # Fetch stored text from Pinecone
        try:
            fetched = pinecone_index.fetch(ids=[str(file_id)], namespace=namespace)
            vector_data = fetched.vectors.get(str(file_id))
            
            if not vector_data or "text" not in vector_data.metadata:
                raise HTTPException(400, "Stored document text missing. Re-upload file.")
            
            document_text = vector_data.metadata["text"].strip()
            
            if not document_text:
                raise HTTPException(400, "Extracted text is empty.")
                
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, f"Failed to retrieve document: {str(e)}")
        
        # Fetch report type
        result = await db.execute(select(ReportType).where(ReportType.report_type_id == report.report_type_id))
        report_type = result.scalar_one_or_none()
        
        if not report_type:
            raise HTTPException(404, "Report type not found")
        
        prompt_template = PROMPTS.get(report_type.name)
        if not prompt_template:
            raise HTTPException(400, f"No analysis prompt for report type: {report_type.name}")
        
        # Prepare OpenAI Prompt
        full_prompt = f"""
{prompt_template}

=== DOCUMENT TEXT TO ANALYZE ===
{document_text}
=== END DOCUMENT TEXT ===

IMPORTANT:
- Return ONLY valid JSON.
- No markdown, no comments, no extra text.
- insights MUST be a ONE-LINE meaningful interpretation.
"""
        
        # OpenAI Call
        try:
            completion = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a medical analysis engine. Always output valid JSON."
                    },
                    {"role": "user", "content": full_prompt}
                ],
                max_tokens=2000,
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            
            ai_response = completion.choices[0].message.content.strip()
            analysis = extract_json_from_text(ai_response)
            
            # Fix schema issues
            analysis.setdefault("summary", "Medical document analyzed successfully")
            analysis.setdefault("key_findings", {})
            analysis.setdefault("recommendations", [])
            
            # Ensure insights is one-liner
            insights_value = analysis.get("insights", "")
            if isinstance(insights_value, list):
                insights_value = " | ".join(map(str, insights_value))
            elif isinstance(insights_value, dict):
                insights_value = " | ".join(f"{k}: {v}" for k, v in insights_value.items())
            insights_value = str(insights_value).replace("\n", " ").strip()
            analysis["insights"] = insights_value[:500]
            
        except Exception as e:
            # Fallback response
            analysis = {
                "summary": "Analysis failed",
                "key_findings": {"error": str(e)},
                "insights": "Analysis failed due to AI processing error.",
                "recommendations": ["Please try again with a clearer document"]
            }
        
        # Update DB
        try:
            medications = analysis.pop("medications", None)
            report.summary = analysis["summary"]
            report.key_findings = analysis["key_findings"]
            report.recommendations = analysis["recommendations"]
            report.insights.update({
                "analysis": analysis,
                "insights_one_line": analysis["insights"],
                "medications": medications,
                "analyzed_at": datetime.now(timezone.utc).isoformat(),
                "document_text_length": len(document_text),
                "namespace": namespace,
            })
            
            db.add(report)
            await db.commit()
            await db.refresh(report)
            
            if medications:
                analysis["medications"] = medications
                
        except Exception as e:
            await db.rollback()
            raise HTTPException(500, f"Failed to update report: {str(e)}")
        
        return analysis
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Analysis failed: {str(e)}")