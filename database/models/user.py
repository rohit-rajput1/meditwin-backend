"""
Defines the User model for a PostgreSQL database using SQLAlchemy ORM.

- Each user has a unique UUID as primary key.
- Stores basic info: name, email, password, and creation timestamp.
- Defines relationships to related tables: profile, health info, reports, dashboards, chats, messages.
"""

from sqlalchemy import String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
import uuid
from database.base import Base

class User(Base):
    __tablename__ = "user"

    # Primary key UUID
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # User details
    user_email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now(timezone.utc))

    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False)
    health_info = relationship("HealthInfo", back_populates="user", uselist=False)
    reports = relationship("Report", back_populates="user", lazy="dynamic")
    dashboards = relationship("Dashboard", back_populates="user", lazy="dynamic")
    chats = relationship("Chat", back_populates="user", lazy="dynamic")
    messages = relationship("Message", back_populates="user", lazy="dynamic")
