import json
import re
import traceback
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
from uuid import UUID
from uuid import uuid4
from database.models.report import Report
from database.models.report_type import ReportType
from database.models.dashboard import Dashboard
from src.dashboard.prompt import (
    PROMPT_MEDICAL_PRESCRIPTION,
    PROMPT_BLOOD_REPORT,
)
from src.upload.dependency import openai_client


# Fetch Report
async def get_report(file_id: UUID, db: AsyncSession):
    try:
        result = await db.execute(
            select(Report).where(Report.report_id == file_id)
        )
        report = result.scalar_one_or_none()
        
        if not report:
            raise HTTPException(404, "Report not found")
        
        if report.status == "processing":
            raise HTTPException(400, "Report is still being processed")
        
        if report.status == "failed":
            raise HTTPException(400, "Report processing failed")
        
        return report
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error fetching report: {str(e)}")


# Fetch Report Type
async def get_report_type(report_type_id: UUID, db: AsyncSession):
    try:
        result = await db.execute(
            select(ReportType).where(ReportType.report_type_id == report_type_id)
        )
        report_type = result.scalar_one_or_none()
        
        if not report_type:
            raise HTTPException(400, "Report type not found")
        
        return report_type
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error fetching report type: {str(e)}")


# JSON Parsing
def safe_json_string(value):
    try:
        if isinstance(value, dict):
            return json.dumps(value, indent=2)
        
        text = str(value).strip()
        
        if not text or text.lower() in ["none", "null", "nan", "undefined"]:
            return ""
        
        try:
            parsed = json.loads(text)
            return json.dumps(parsed, indent=2)
        except:
            pass
        
        text = text.replace("'", '"')
        text = re.sub(r'([{,]\s*)([A-Za-z0-9_]+)(\s*:)', r'\1"\2"\3', text)
        text = re.sub(r'([{,]\s*)"([A-Za-z0-9_]+)"\s*(?=[},])', r'\1"\2": ""', text)
        
        try:
            parsed = json.loads(text)
            return json.dumps(parsed, indent=2)
        except:
            return text
    
    except Exception:
        return str(value)


# Prompt Preparing
def prepare_prompt(report_type_name: str, report: Report):
    try:
        parts = []
        
        if report.summary:
            parts.append(f"Summary:\n{safe_json_string(report.summary)}")
        
        if report.key_findings:
            parts.append(f"Key Findings:\n{safe_json_string(report.key_findings)}")
        
        if report.insights:
            parts.append(f"Insights:\n{safe_json_string(report.insights)}")
        
        if report.recommendations:
            parts.append(f"Recommendations:\n{safe_json_string(report.recommendations)}")
        
        final_text = "\n\n".join(parts) if parts else "No report data available"
        
        # Simple string replacement instead of format()
        if "prescription" in report_type_name:
            prompt = PROMPT_MEDICAL_PRESCRIPTION.replace("{report_text}", final_text)
            return prompt, "prescription"
        
        if "blood" in report_type_name or "test" in report_type_name:
            prompt = PROMPT_BLOOD_REPORT.replace("{report_text}", final_text)
            return prompt, "blood_test"
        
        raise HTTPException(400, f"Unsupported report type: {report_type_name}")
    
    except Exception as e:
        raise HTTPException(500, f"Error preparing prompt: {str(e)}")

# OpenAI Call
async def extract_dashboard_data_from_llm(prompt: str, dashboard_type: str):
    try:
        system_prompt = (
            "You are a medical prescription analysis expert. "
            "Extract ONLY real data from prescriptions. "
            "NEVER use placeholders like 'Medicine 1', 'Not specified', 'As prescribed'. "
            "Return EXACTLY 4 metrics in topBar. "
            "If data is missing, omit the field entirely."
            if dashboard_type == "prescription"
            else "You are a blood report analysis expert. "
            "Extract ALL biomarkers with actual values. "
            "Calculate status accurately based on reference ranges. "
            "Return EXACTLY 4 metrics in topBar."
        )
        
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        
        text = response.choices[0].message.content.strip()
        dashboard_data = json.loads(text)
        
        return {
            "topBar": dashboard_data.get("topBar", {}),
            "middleSection": dashboard_data.get("middleSection", {}),
            "recommendations": dashboard_data.get("recommendations", []),
            "criticalInsights": dashboard_data.get("criticalInsights", []),
        }
    
    except json.JSONDecodeError as e:
        raise HTTPException(500, f"Invalid JSON returned by LLM: {str(e)}")
    except Exception as e:
        raise HTTPException(500, f"Error extracting data from LLM: {str(e)}")


# Validate Dashboard Data
def validate_dashboard_data(dashboard_data: dict, dashboard_type: str):
    """Validate and clean dashboard data to remove placeholders and ensure data quality"""
    try:
        # Clean topBar - remove empty or placeholder values
        if "topBar" in dashboard_data:
            top_bar = dashboard_data["topBar"]
            
            # Remove any "Not specified", empty values, or generic placeholders
            cleaned_top_bar = {
                k: v for k, v in top_bar.items() 
                if v and str(v).strip() not in [
                    "Not specified", "None", "", "null", "Not available",
                    "N/A", "NA", "Unknown", "TBD", "To be determined"
                ]
            }
            
            # Ensure exactly 4 keys (take first 4 if more, pad if less)
            if len(cleaned_top_bar) > 4:
                # Priority order for prescription
                if dashboard_type == "prescription":
                    priority_keys = [
                        "diagnosisTreatment", "medicationCount", 
                        "prescriptionDate", "followUpDate",
                        "treatmentDuration", "prescribingDoctorInfo",
                        "nextTestOrInvestigation", "severityOrCategory"
                    ]
                # Priority order for blood test
                else:
                    priority_keys = [
                        "overallReportStatus", "abnormalValueCount",
                        "mostCriticalMarker", "reportDate"
                    ]
                
                # Select top 4 based on priority
                final_top_bar = {}
                for key in priority_keys:
                    if key in cleaned_top_bar and len(final_top_bar) < 4:
                        final_top_bar[key] = cleaned_top_bar[key]
                
                dashboard_data["topBar"] = final_top_bar
            else:
                dashboard_data["topBar"] = cleaned_top_bar
        
        # Validate prescription middleSection
        if dashboard_type == "prescription" and "middleSection" in dashboard_data:
            middle = dashboard_data["middleSection"]
            
            # Filter out placeholder medicines
            if "medicines" in middle and isinstance(middle["medicines"], list):
                valid_medicines = []
                
                for med in middle["medicines"]:
                    med_name = med.get("name", "").strip()
                    
                    # Skip if medicine has placeholder name
                    if (med_name and 
                        not med_name.startswith("Medicine ") and
                        med_name.lower() not in ["medicine", "medication", "drug", "not specified", "unknown"]):
                        
                        # Clean medicine info
                        if "medicineInfo" in med:
                            med["medicineInfo"] = {
                                k: v for k, v in med["medicineInfo"].items()
                                if v and str(v).strip() not in [
                                    "Not specified", "Standard dose", "As prescribed",
                                    "Medical purpose", "None specified"
                                ]
                            }
                        
                        # Clean dosage instruction
                        if "dosageInstruction" in med:
                            med["dosageInstruction"] = {
                                k: v for k, v in med["dosageInstruction"].items()
                                if v and str(v).strip() not in [
                                    "Not specified", "As advised", "As prescribed",
                                    "As per schedule", "None specified"
                                ]
                            }
                        
                        # Remove empty sideEffects and warnings
                        if med.get("sideEffects") in ["Not specified", "None specified", ""]:
                            med.pop("sideEffects", None)
                        
                        if med.get("warnings") in ["Not specified", "None specified", ""]:
                            med.pop("warnings", None)
                        
                        valid_medicines.append(med)
                
                middle["medicines"] = valid_medicines
                
                # Update medication count in topBar
                if "topBar" in dashboard_data:
                    dashboard_data["topBar"]["medicationCount"] = len(valid_medicines)
            
            # Ensure safetyInformation exists
            if "safetyInformation" not in middle:
                middle["safetyInformation"] = {
                    "dietaryRestrictions": [],
                    "lifestyleRecommendations": [],
                    "drugInteractions": []
                }
        
        # Validate blood test middleSection
        if dashboard_type == "blood_test" and "middleSection" in dashboard_data:
            middle = dashboard_data["middleSection"]
            
            # Ensure biomarkerChart exists
            if "biomarkerChart" not in middle:
                middle["biomarkerChart"] = []
            
            # Ensure chart structures exist
            if "cbcTrendChart" not in middle:
                middle["cbcTrendChart"] = {}
            
            if "cholesterolBreakdownChart" not in middle:
                middle["cholesterolBreakdownChart"] = {}
            
            # Validate biomarkers have required fields
            if isinstance(middle.get("biomarkerChart"), list):
                valid_biomarkers = [
                    bio for bio in middle["biomarkerChart"]
                    if bio.get("testName") and 
                       bio.get("currentValue") is not None and
                       bio.get("status")
                ]
                middle["biomarkerChart"] = valid_biomarkers
        
        # Clean recommendations - remove generic ones
        if "recommendations" in dashboard_data:
            dashboard_data["recommendations"] = [
                rec for rec in dashboard_data["recommendations"]
                if rec and len(rec.strip()) > 10 and
                not any(generic in rec.lower() for generic in [
                    "take all medications as prescribed",
                    "follow specific dosing schedules carefully",
                    "consult healthcare provider"
                ])
            ][:4]  # Limit to 4 recommendations
        
        # Clean critical insights - remove generic ones
        if "criticalInsights" in dashboard_data:
            dashboard_data["criticalInsights"] = [
                insight for insight in dashboard_data["criticalInsights"]
                if insight and len(insight.strip()) > 15 and
                not any(generic in insight.lower() for generic in [
                    "prescription analysis complete",
                    "medications prescribed with unspecified"
                ])
            ][:3]  # Limit to 3 insights
        
        return dashboard_data
    
    except Exception as e:
        raise HTTPException(500, f"Error validating dashboard data: {str(e)}")


# Dashboard Creation
async def create_dashboard(file_id: UUID, db: AsyncSession):
    try:
        # Fetch report details
        report_query = await db.execute(
            select(Report).where(Report.report_id == file_id)
        )
        report = report_query.scalar_one_or_none()
        if not report:
            raise HTTPException(404, "Report not found.")

        # Check if dashboard already exists for THIS report_id
        existing_query = await db.execute(
            select(Dashboard).where(Dashboard.report_id == report.report_id)
        )
        existing_dashboard = existing_query.scalar_one_or_none()
        
        if existing_dashboard:
            return existing_dashboard

        # Fetch report type
        report_type_query = await db.execute(
            select(ReportType).where(ReportType.report_type_id == report.report_type_id)
        )
        report_type = report_type_query.scalar_one_or_none()
        if not report_type:
            raise HTTPException(404, "Report type not found.")

        # Generate prompt + dashboard type
        prompt, dashboard_type = prepare_prompt(
            report_type.name.lower(), report
        )

        # Extract dashboard data from LLM
        extracted_data = await extract_dashboard_data_from_llm(
            prompt, dashboard_type
        )

        # Validate + normalize
        validated = validate_dashboard_data(
            extracted_data, dashboard_type
        )

        # Create NEW dashboard with NEW dashboard_id for report_id
        dashboard = Dashboard(
            dashboard_id=uuid4(),
            dashboard_type=dashboard_type,
            user_id=report.user_id,
            report_id=report.report_id, 
            report_type_id=report.report_type_id,
            top_bar=validated["topBar"],
            middle_section=validated["middleSection"],
            recommendations=validated["recommendations"],
            critical_insights=validated["criticalInsights"],
        )
        
        db.add(dashboard)
        
        try:
            await db.commit()
            await db.refresh(dashboard)
            return dashboard
        except Exception as commit_error:
            await db.rollback()
            # Handle race condition where another request created dashboard
            if "duplicate key" in str(commit_error).lower() and "report_id" in str(commit_error).lower():
                # Another request just created a dashboard for this report_id
                retry_query = await db.execute(
                    select(Dashboard).where(Dashboard.report_id == report.report_id)
                )
                existing = retry_query.scalar_one_or_none()
                if existing:
                    return existing
            # Re-raise if it's a different error
            raise HTTPException(500, f"Database error: {str(commit_error)}")

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        traceback.print_exc()
        raise HTTPException(500, f"Dashboard creation failed: {str(e)}")
    
async def get_dashboard_by_file_id(file_id: UUID, db: AsyncSession):
    query = await db.execute(
        select(Report).where(Report.report_id == file_id)
    )
    report = query.scalar_one_or_none()

    if not report:
        raise HTTPException(404, "Report not found.")

    dashboard_query = await db.execute(
        select(Dashboard).where(Dashboard.report_id == report.report_id)
    )
    dashboard = dashboard_query.scalar_one_or_none()

    if not dashboard:
        raise HTTPException(404, "Dashboard not found for this file.")

    return dashboard