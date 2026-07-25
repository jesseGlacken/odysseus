"""Extracted from core/database.py for ODY-73 (P2.5b).

See ADR-0011 and the ODY-21 extraction pattern for rationale.
"""
from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import backref, relationship

from core.base import Base, TimestampMixin


class CrewMember(TimestampMixin, Base):
    """A custom AI persona ('crew member') with its own personality, model, tools, and memory scope."""
    __tablename__ = "crew_members"

    id            = Column(String, primary_key=True, index=True)
    owner         = Column(String, nullable=True, index=True)
    name          = Column(String, nullable=False)
    avatar        = Column(String, nullable=True)
    user_name     = Column(String, nullable=True)          # what they call the user
    personality   = Column(Text, nullable=True)             # system prompt
    model         = Column(String, nullable=True)
    endpoint_url  = Column(String, nullable=True)
    greeting      = Column(Text, nullable=True)
    enabled_tools = Column(Text, nullable=True)             # JSON array or "all"
    session_id    = Column(String, ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True)
    is_active     = Column(Boolean, default=True)
    sort_order    = Column(Integer, default=0)
    is_default_assistant = Column(Boolean, default=False)   # singleton per-owner "personal assistant"
    timezone      = Column(String, nullable=True)           # IANA tz name (e.g. "America/New_York") for scheduled check-ins

    session = relationship("Session", foreign_keys=[session_id],
                           backref=backref("crew_member", uselist=False))



