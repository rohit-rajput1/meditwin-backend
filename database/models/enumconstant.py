"""
Defines an enumeration for report types.

- `blood_report`: Represents a blood report.
- `prescription`: Represents a prescription document.
"""

import enum

class ReportTypeEnum(str, enum.Enum):
    blood_report = "blood_report"
    prescription = "prescription"
