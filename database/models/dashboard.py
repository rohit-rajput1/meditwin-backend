"""
Defines the Dashboard model for a PostgreSQL database using SQLAlchemy ORM.

- Each dashboard has a unique UUID as primary key.
- Linked to a User (one-to-many relationship).
- Stores dashboard data including report type, metrics, and charts in JSON format.
- Tracks creation timestamp.
"""

from sqlalchemy import ForeignKey, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
import uuid
from database.base import Base
from .report_type import ReportType    

class Dashboard(Base):
    __tablename__ = "dashboard"

    # Primary key UUID
    dashboard_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key linking to User
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user.user_id"))

    # Foreign key to ReportType
    report_type_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("report_type.report_type_id"))

    # Dashboard details
    metrics: Mapped[dict] = mapped_column(JSON)
    charts: Mapped[dict] = mapped_column(JSON)

    # Timestamp for creation
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="dashboards")  # One-to-many link to User
    report_type = relationship("ReportType")  # Link to report_type table
