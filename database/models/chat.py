"""
Defines the Chat model for a PostgreSQL database using SQLAlchemy ORM.

- Each chat has a unique UUID as primary key.
- Stores chat name, context, timestamps, creator, and optional linked report.
- Linked to User (creator), Report, and contains multiple Messages (one-to-many).
"""

from sqlalchemy import String, DateTime, ForeignKey, JSON,Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
import uuid
from database.base import Base

class Chat(Base):
    __tablename__ = "chat"

    # Primary key UUID
    chat_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Chat details
    chat_name: Mapped[str] = mapped_column(String)
    is_valid_chat: Mapped[bool] = mapped_column(Boolean, default=True)
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=datetime.now(timezone.utc), 
        onupdate=datetime.now(timezone.utc)
    )

    # Foreign keys
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user.user_id"))
    file_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("report.report_id"), nullable=True)

    # Relationships
    user = relationship("User", back_populates="chats")  # Chat creator
    report = relationship("Report", back_populates="chats")  # Optional linked report
    messages = relationship("Message", back_populates="chat", lazy="dynamic")  # One-to-many messages
