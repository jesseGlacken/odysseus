"""Extracted from core/database.py for ODY-73 (P2.5b)."""
from __future__ import annotations

from sqlalchemy import Boolean, Column, String
from sqlalchemy.dialects.sqlite import JSON

from core.base import Base, TimestampMixin


class Integration(TimestampMixin, Base):
    """An external service connection (email, RSS, webhook, etc.)."""
    __tablename__ = "integrations"

    id     = Column(String, primary_key=True, index=True)
    owner  = Column(String, nullable=True, index=True)
    name   = Column(String, nullable=False)
    type   = Column(String, nullable=False)  # "email", "rss", "webhook"
    config = Column(JSON, nullable=True)     # type-specific config
    enabled = Column(Boolean, default=True)
