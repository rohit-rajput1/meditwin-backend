from sqlalchemy import ForeignKey, DateTime, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
import uuid
from database.base import Base


class Dashboard(Base):
    __tablename__ = "dashboard"

    dashboard_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.user_id"), nullable=False
    )

    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("report.report_id"), nullable=False, unique=True
    )

    report_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("report_type.report_type_id"), nullable=False
    )

    dashboard_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    top_bar: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    middle_section: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    recommendations: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    critical_insights: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
        nullable=False,
    )

    user = relationship("User", back_populates="dashboards")
    report = relationship("Report", back_populates="dashboard")
    report_type = relationship("ReportType", back_populates="dashboards")
