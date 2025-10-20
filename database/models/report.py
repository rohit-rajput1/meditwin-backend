"""
Defines the Report model for a PostgreSQL database using SQLAlchemy ORM.

- Each report has a unique UUID as primary key.
- Linked to a User (one-to-many relationship).
- Stores report type, file URL, summary, key findings, insights, and recommendations.
- Uses JSON columns for structured data.
- Tracks upload timestamp.
- Related to Chat model for discussions on the report.
"""

from sqlalchemy import String, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
import uuid
from database.base import Base
from .enumconstant import ReportTypeEnum

class Report(Base):
    __tablename__ = "report"

    # Primary key UUID
    report_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key linking to User
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user.user_id"))

    # Report details
    report_type: Mapped[ReportTypeEnum] = mapped_column(Enum(ReportTypeEnum))
    report_file_url: Mapped[str] = mapped_column(String)
    summary: Mapped[dict] = mapped_column(JSON)
    key_findings: Mapped[dict] = mapped_column(JSON)
    insights: Mapped[dict] = mapped_column(JSON)
    recommendations: Mapped[dict] = mapped_column(JSON)

    # Upload timestamp
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="reports")  # Each report belongs to a user
    chats = relationship("Chat", back_populates="report", lazy="dynamic")  # One-to-many chats
