"""core.models.session_models — Session and ChatMessage ORM models (ODY-21 / P2.5).

Extracted from core/database.py so callers can import the chat-session
aggregate directly from ``core.models.session_models`` instead of from the
monolithic database module.

Backward-compat shim in ``core.database`` re-exports both classes, so the
original ``from core.database import Session, ChatMessage`` still works for
all existing importers.
"""
from __future__ import annotations

from sqlalchemy import (
    Column,
    String,
    Text,
    Boolean,
    DateTime,
    Integer,
    ForeignKey,
    JSON,
    Index,
    func,
)
from sqlalchemy.orm import relationship

from core.base import Base, EncryptedText, TimestampMixin, utcnow_naive


class Session(TimestampMixin, Base):
    """
    SQLAlchemy model for Session table.
    Represents a chat session with its configuration and metadata.
    """
    __tablename__ = "sessions"

    # Primary key
    id = Column(String, primary_key=True, index=True)

    # Session metadata
    name = Column(String, nullable=False)
    endpoint_url = Column(String, nullable=False)
    model = Column(String, nullable=False)
    owner = Column(String, nullable=True, index=True)  # username; null = legacy/shared

    # Configuration flags
    rag = Column(Boolean, default=False)
    archived = Column(Boolean, default=False)

    # Organization
    folder = Column(String, nullable=True, default=None)

    # Headers stored as JSON
    headers = Column(JSON, default=dict)

    # Timestamps are provided by TimestampMixin
    last_accessed = Column(DateTime, default=func.now(), onupdate=func.now())
    # Timestamp of the last actual MESSAGE in this session. Set explicitly
    # only when a message is persisted (NOT onupdate) — so it's a clean
    # "last conversation" signal, immune to renames / model swaps / merely
    # opening the chat (all of which bump updated_at and last_accessed).
    # The "Last active" sort uses this.
    last_message_at = Column(DateTime, nullable=True, default=None)

    # Indexes - optimized composites
    __table_args__ = (
        Index('ix_sessions_active', 'archived', 'last_accessed'),
        Index('ix_sessions_search', 'name', 'archived'),
    )

    # Properties
    is_important = Column(Boolean, default=False)
    message_count = Column(Integer, default=0)
    total_input_tokens = Column(Integer, default=0)
    total_output_tokens = Column(Integer, default=0)
    mode = Column(String, nullable=True)  # 'agent', 'chat', or 'research'
    crew_member_id = Column(String, nullable=True)  # links to crew_members.id

    # Relationship to chat messages
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

    @property
    def is_active(self):
        """Check if session is active (not archived)"""
        return not self.archived

    def to_dict(self):
        """Convert session to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'model': self.model,
            'endpoint_url': self.endpoint_url,
            'rag': self.rag,
            'archived': self.archived,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None,
            'last_message_at': self.last_message_at.isoformat() if self.last_message_at else None,
            'message_count': self.message_count,
            'is_important': self.is_important,
            'folder': self.folder,
            'total_input_tokens': self.total_input_tokens or 0,
            'total_output_tokens': self.total_output_tokens or 0,
            'crew_member_id': self.crew_member_id,
        }


class ChatMessage(Base):
    """
    SQLAlchemy model for ChatMessage table.
    Represents individual chat messages within a session.
    """
    __tablename__ = "chat_messages"

    # Primary key - using String to support UUIDs
    id = Column(String, primary_key=True, index=True)

    # Foreign key to Session
    session_id = Column(String, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)

    # Message content
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    meta_data = Column("metadata", Text, nullable=True)  # JSON string for metrics etc.

    # Timestamp
    timestamp = Column(DateTime, default=utcnow_naive)

    # Relationship to Session
    session = relationship("Session", back_populates="messages")

    # Indexes - optimized composite
    __table_args__ = (
        Index('ix_messages_session_time', 'session_id', 'timestamp'),  # Composite for efficient message retrieval
    )
