from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
from uuid import UUID
from database.models.report import Report
from database.models.report_type import ReportType
from database.models.dashboard import Dashboard

# Fetch Report
async def get_report(file_id: UUID, db: AsyncSession):
    result = await db.execute(select(Report).where(Report.report_id == file_id))
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(404, "Report not found")
    if report.status == "processing":
        raise HTTPException(400, "Report is still being processed")
    if report.status == "failed":
        raise HTTPException(400, "Report processing failed")

    return report

# Build JSON for Prescription Dashboard
def build_prescription_dashboard(report: Report):
    key = report.key_findings or {}
    insights = report.insights or {}
    recs = report.recommendations or []

    return {
        "diagnosis": key.get("Diagnosis", ""),
        "treatment_duration": key.get("Treatment Duration", ""),
        "medications_count": key.get("Medications Prescribed", "0"),
        "follow_up_date": key.get("Follow-up Required", ""),
        "medicines": insights.get("medications", []),
        "recommendations": recs
    }

# Build JSON for Blood Test Dashboard
def build_blood_test_dashboard(report: Report):
    insights = report.insights or {}
    recs = report.recommendations or []

    return {
        "vitals": insights.get("vitals", {}),
        "bp_trend": insights.get("bp_trend", {}),
        "weight_progress": insights.get("weight_progress", {}),
        "cholesterol_chart": insights.get("cholesterol_chart", {}),
        "recent_reports": insights.get("recent_reports", []),
        "health_tips": recs
    }


# Create Dashboard (Main Logic)
async def create_dashboard(file_id: UUID, db: AsyncSession):
    report = await get_report(file_id, db)

    # Fetch report type
    res = await db.execute(
        select(ReportType).where(ReportType.report_type_id == report.report_type_id)
    )
    report_type = res.scalar_one_or_none()

    if not report_type:
        raise HTTPException(400, "Report type missing")

    rtype = report_type.name.lower()

    # Decide dashboard structure
    if rtype == "medical_prescription":
        dashboard_json = build_prescription_dashboard(report)
        dashboard_type = "prescription"

    elif rtype == "blood_test_report":
        dashboard_json = build_blood_test_dashboard(report)
        dashboard_type = "blood_test"

    else:
        raise HTTPException(400, f"Unsupported dashboard type: {report_type.name}")

    # Insert into DB
    dashboard = Dashboard(
        user_id=report.user_id,
        report_type_id=report.report_type_id,
        metrics={"type": dashboard_type},
        charts=dashboard_json,
    )

    db.add(dashboard)
    await db.commit()
    await db.refresh(dashboard)

    return {
        "dashboard_id": dashboard.dashboard_id,
        "dashboard_type": dashboard_type,
        "data": dashboard_json
    }
