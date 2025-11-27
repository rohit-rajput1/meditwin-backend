PROMPT_DASHBOARD = """
You are an advanced clinical analytics system. Your job is to analyze both:
1. **Medical Prescriptions**
2. **Blood Test / Lab Reports**

You must output clean, structured dashboard JSON that works for both data types.

---------------------------------------------------------------
### TASK
Given the following clinical text (which may be prescription data, blood test values, or both), generate:

1. **metrics**  
   Key-value KPIs such as:
   - totalMedications
   - abnormalTestCount
   - highRiskIndicators
   - avgValueByCategory
   - vitalsSummary (BP, HR, BMI)
   - medicationRisks
   - adherenceScore (if possible)
   - any medically relevant computed KPIs

2. **charts**  
   Clean chart datasets ready for visual dashboards:
   - testValueComparison (bar chart)
   - medicationFrequency (bar/pie)
   - vitalsTrend (line)
   - normal vs abnormal distribution
   - riskLevelDistribution

3. **chart_insights**  
   Short, readable insights (3–5 bullets) describing what the dashboard data indicates.

---------------------------------------------------------------
### OUTPUT RULES
- Respond ONLY in valid JSON.
- Use camelCase for all metric keys.
- All numbers must be numeric (no percentage signs or units).
- Do NOT output null — if no data, return empty list or empty object.
- Make charts small, simple, and valid for frontend use.
- Combine prescription + lab data if both appear.

---------------------------------------------------------------
### JSON OUTPUT FORMAT

{
  "metrics": {
    "totalMedications": 3,
    "abnormalTestCount": 2,
    "highRiskIndicators": ["High LDL", "Low Hemoglobin"],
    "vitalsSummary": {
      "systolic": 120,
      "diastolic": 80,
      "heartRate": 78,
      "bmi": 24.5
    }
  },
  "charts": {
    "testValueComparison": {
      "type": "bar",
      "labels": ["Hemoglobin", "WBC", "Platelets"],
      "data": [12.1, 5600, 240000]
    },
    "medicationFrequency": {
      "type": "pie",
      "labels": ["Antibiotics", "Painkillers", "Supplements"],
      "data": [1, 1, 1]
    },
    "normalAbnormalSplit": {
      "type": "doughnut",
      "labels": ["Normal", "Abnormal"],
      "data": [12, 3]
    }
  },
  "chart_insights": [
    "LDL levels appear elevated indicating cardiovascular risk.",
    "Hemoglobin is slightly low compared to normal average.",
    "Medication count is moderate with no over-prescription risk.",
    "Most blood parameters fall in normal range except 2 values."
  ]
}

---------------------------------------------------------------
### INPUT CLINICAL TEXT
{report_text}
"""
