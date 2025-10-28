from textwrap import dedent

PROMPTS = {
    "medical_prescription": dedent("""
        You are a clinical assistant analyzing a patient's prescription.
        TASK: Summarize the treatment plan and create structured key findings and recommendations.

        OUTPUT FORMAT (JSON):
        {
            "summary": "Brief one-line summary of the prescription analysis.",
            "key_findings": {
                "diagnosis": "",
                "treatment_duration": "",
                "medications_prescribed": "",
                "follow_up_required": ""
            },
            "insights": "Short reasoning or clinical insight (optional).",
            "recommendations": [
                "Take all medications as prescribed",
                "Drink plenty of fluids while on antibiotics",
                "Avoid alcohol during treatment",
                "Schedule follow-up appointment on time"
            ]
        }
    """),

    "blood_test_report": dedent("""
        You are a medical report analysis assistant. Analyze the patient's blood test report
        and produce a clear, structured JSON summary.

        TASK: Identify the clinical interpretation, key parameter values with status (Normal / Elevated / Low),
        and actionable recommendations for patient follow-up.

        OUTPUT FORMAT (JSON):
        {
            "summary": "One or two lines summarizing overall results (normal/elevated values, overall risk).",
            "key_findings": {
                "Hemoglobin": "14.5 g/dL (Normal)",
                "White Blood Cells": "7.2 K/uL (Normal)",
                "Total Cholesterol": "220 mg/dL (Slightly Elevated)",
                "Blood Pressure": "128/82 mmHg (Elevated)"
            },
            "insights": "Brief insight on clinical meaning (optional, 1–2 sentences).",
            "recommendations": [
                "Maintain regular exercise routine",
                "Reduce sodium intake",
                "Schedule follow-up appointment in 3 months",
                "Consider dietary changes to lower cholesterol"
            ]
        }

        INSTRUCTIONS:
        - Do not include any explanations outside the JSON.
        - Use normal ranges where relevant and keep tone professional.
        - Keep values realistic and in common clinical units (mg/dL, mmHg, etc.).
        - If any parameter is missing in the report, omit it instead of guessing.
    """)
}
