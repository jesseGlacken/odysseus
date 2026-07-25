"""Extracted from core/database.py for ODY-73 (P2.5b)."""
from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from core.base import Base
from core.base import utcnow_naive


class Memory(Base):
    """
    SQLAlchemy model for Memory table.
    Represents persistent memory entries with metadata.
    """
    __tablename__ = "memories"

    # Primary key
    id = Column(String, primary_key=True, index=True)

    # Memory content
    text = Column(Text, nullable=False)

    # Categorization
    category = Column(String, default='fact')
    source = Column(String, default='user')

    # Owner (username)
    owner = Column(String, nullable=True, index=True)

    # Reference to session (nullable)
    session_id = Column(String, ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True, index=True)

    # Timestamp as Unix timestamp
    timestamp = Column(Integer, default=lambda: int(utcnow_naive().timestamp()))

    # Relationship to Session
    session = relationship("Session", backref="memories")

    # Indexes - optimized composites
    __table_args__ = (
        Index('ix_memories_lookup', 'category', 'timestamp'),
        Index('ix_memories_session', 'session_id', 'timestamp'),
    )
