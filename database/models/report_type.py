import uuid
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.base import Base


class ReportType(Base):
    __tablename__ = "report_type"

    report_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    reports = relationship("Report", back_populates="report_type")

    dashboards = relationship("Dashboard", back_populates="report_type")
