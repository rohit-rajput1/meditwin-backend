"""
Defines the Report model for a PostgreSQL database using SQLAlchemy ORM.

- Each report has a unique UUID as primary key.
- Linked to a User (one-to-many relationship).
- Stores report type, file URL, summary, key findings, insights, and recommendations.
- Uses JSON columns for structured data.
- Tracks upload timestamp.
- Related to Chat model for discussions on the report.
"""

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
import uuid
from datetime import datetime, timezone
from database.base import Base
from .report_type import ReportType

class Report(Base):
    __tablename__ = "report"

    report_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user.user_id"))
    report_type_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("report_type.report_type_id"))
    summary: Mapped[dict] = mapped_column(JSON, nullable=True)
    key_findings: Mapped[dict] = mapped_column(JSON, nullable=True)
    insights: Mapped[dict] = mapped_column(JSON, nullable=True)
    recommendations: Mapped[dict] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String, default="processing")

    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="reports")
    chats = relationship("Chat", back_populates="report", lazy="dynamic")
    report_type = relationship("ReportType", back_populates="reports")