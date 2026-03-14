"""
Defines the Message model for a PostgreSQL database using SQLAlchemy ORM.

- Each message has a unique UUID as primary key.
- Linked to a Chat (one-to-many relationship).
- Stores user query, bot response, metadata, and creation timestamp.
"""

from sqlalchemy import ForeignKey, DateTime, Text, JSON, String,Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
import uuid
from database.base import Base

class Message(Base):
    __tablename__ = "message"

    message_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chat.chat_id"))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user.user_id"))
    user_query: Mapped[str] = mapped_column(String)
    bot_response: Mapped[str] = mapped_column(Text)
    metadatas: Mapped[dict] = mapped_column(JSON)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now(timezone.utc))

    # Relationship to Chat
    chat = relationship("Chat", back_populates="messages")
    user = relationship("User", back_populates="messages")