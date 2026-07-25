"""Extracted from core/database.py for ODY-73 (P2.5b).

See ADR-0011 and the ODY-21 extraction pattern for rationale.
"""
from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Index,
)
from sqlalchemy.orm import backref, relationship

from core.base import Base, TimestampMixin
from core.base import utcnow_naive


class UserTool(TimestampMixin, Base):
    """User-created sandboxed mini-apps/tools."""
    __tablename__ = "user_tools"

    id            = Column(String, primary_key=True, index=True)
    name          = Column(String, nullable=False)
    description   = Column(Text, nullable=True)
    icon          = Column(String, nullable=True, default="")
    html_content  = Column(Text, nullable=False)
    scope         = Column(String, nullable=False, default="global")  # "global" or session_id
    session_id    = Column(String, ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True)
    owner         = Column(String, nullable=True, index=True)      # username
    is_pinned     = Column(Boolean, default=False)
    is_active     = Column(Boolean, default=True)
    version       = Column(Integer, default=1)
    author        = Column(String, nullable=True, default="ai")

    session = relationship("Session", backref=backref("user_tools", cascade="all, delete-orphan"))

    __table_args__ = (
        Index('ix_user_tools_scope', 'scope'),
        Index('ix_user_tools_active', 'is_active'),
    )



class UserToolData(Base):
    """Key-value storage for user tool persistent data."""
    __tablename__ = "user_tool_data"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    tool_id    = Column(String, ForeignKey("user_tools.id", ondelete="CASCADE"), nullable=False)
    key        = Column(String, nullable=False)
    value      = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow_naive)
    updated_at = Column(DateTime, default=utcnow_naive, onupdate=utcnow_naive)

    tool = relationship("UserTool", backref=backref("data_entries", cascade="all, delete-orphan"))

    __table_args__ = (
        Index('ix_user_tool_data_tool_key', 'tool_id', 'key', unique=True),
    )



