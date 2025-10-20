"""
Defines the HealthInfo model for a PostgreSQL database using SQLAlchemy ORM.

- Each record has a unique UUID as primary key.
- Linked to a User via foreign key (one-to-one relationship).
- Stores health-related data: height, weight, blood type, emergency contact, allergies, and current medications.
- Tracks the last update timestamp.
"""

from sqlalchemy import Float, String, DateTime, ForeignKey, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
import uuid
from database.base import Base

class HealthInfo(Base):
    __tablename__ = "health_info"

    # Primary key UUID
    health_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key linking to User
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user.user_id"))

    # Health details
    height_cm: Mapped[float] = mapped_column(Float)
    weight_kg: Mapped[float] = mapped_column(Float)
    blood_type: Mapped[str] = mapped_column(String)
    emergency_contact: Mapped[str] = mapped_column(String)
    allergies: Mapped[list[str]] = mapped_column(ARRAY(String))
    current_medications: Mapped[list[str]] = mapped_column(ARRAY(String))

    # Timestamp for updates
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=datetime.now(timezone.utc), 
        onupdate=datetime.now(timezone.utc)
    )

    # Relationship to User
    user = relationship("User", back_populates="health_info")  # One-to-one link to User
