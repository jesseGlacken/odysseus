"""Extracted from core/database.py for ODY-73 (P2.5b).

See ADR-0011 and the ODY-21 extraction pattern for rationale.
"""
from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Index,
)
from sqlalchemy.orm import relationship

from core.base import Base, TimestampMixin
from core.base import EncryptedText, utcnow_naive


class ApiToken(TimestampMixin, Base):
    """API tokens for external integrations (n8n, Make, etc.)."""
    __tablename__ = "api_tokens"

    id = Column(String, primary_key=True, index=True)
    owner = Column(String, nullable=True, index=True)
    name = Column(String, nullable=False)
    token_hash = Column(String, nullable=False)
    token_prefix = Column(String, nullable=False)  # first 8 chars for display
    scopes = Column(String, nullable=False, default="chat")
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime, nullable=True)



class Webhook(TimestampMixin, Base):
    """Outgoing webhooks fired on events."""
    __tablename__ = "webhooks"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    secret = Column(String, nullable=True)  # HMAC-SHA256 signing secret
    events = Column(String, nullable=False)  # comma-separated event types
    is_active = Column(Boolean, default=True)
    last_triggered_at = Column(DateTime, nullable=True)
    last_status_code = Column(Integer, nullable=True)
    last_error = Column(String, nullable=True)



