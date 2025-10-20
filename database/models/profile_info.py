"""
Defines the UserProfile model for a PostgreSQL database using SQLAlchemy ORM.

- Each profile has a unique UUID as primary key.
- Linked to a User via foreign key (one-to-one relationship).
- Stores personal details: first name, last name, phone, location, and date of birth.
- Tracks creation and last update timestamps.
"""

from sqlalchemy import String, DateTime, Date, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
import uuid
from database.base import Base

class UserProfile(Base):
    __tablename__ = "user_profile"

    # Primary key UUID
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key linking to User
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user.user_id"))

    # Profile details
    first_name: Mapped[str] = mapped_column(String)
    last_name: Mapped[str] = mapped_column(String)
    phone: Mapped[str] = mapped_column(String)
    location: Mapped[str] = mapped_column(String)
    date_of_birth: Mapped[Date] = mapped_column(Date)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=datetime.now(timezone.utc), 
        onupdate=datetime.now(timezone.utc)
    )

    # Relationship to User
    user = relationship("User", back_populates="profile")  # One-to-one link to User
