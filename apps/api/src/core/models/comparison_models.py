"""Extracted from core/database.py for ODY-73 (P2.5b).

See ADR-0011 and the ODY-21 extraction pattern for rationale.
"""
from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    Text,
    Index,
)

from core.base import Base, TimestampMixin
from core.base import EncryptedText


class Comparison(TimestampMixin, Base):
    """Stores A/B model comparison results."""
    __tablename__ = "comparisons"

    id = Column(String, primary_key=True, index=True)
    session_id = Column(String, nullable=True)     # Parent session context (optional)
    owner = Column(String, nullable=True, index=True)  # username
    prompt = Column(Text, nullable=False)
    model_a = Column(String, nullable=False)
    model_b = Column(String, nullable=False)
    endpoint_a = Column(String, nullable=False)
    endpoint_b = Column(String, nullable=False)
    response_a = Column(Text, nullable=True)
    response_b = Column(Text, nullable=True)
    metrics_a = Column(Text, nullable=True)         # JSON string
    metrics_b = Column(Text, nullable=True)         # JSON string
    winner = Column(String, nullable=True)           # "a", "b", "tie", or null
    is_blind = Column(Boolean, default=True)
    blind_mapping = Column(Text, nullable=True)      # JSON: {"left": "a"/"b", "right": "a"/"b"}
    voted_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index('ix_comparisons_voted_at', 'voted_at'),
    )



class Signature(TimestampMixin, Base):
    """User-saved visual signatures (image stamps).

    Reusable across PDF form filling, email composition, and document editing.
    `data_png` is a base64-encoded PNG (no `data:` prefix). The SVG vector
    column is reserved for future smooth vector storage. Both are stored
    Fernet-encrypted at rest (see EncryptedText / src.secret_storage); a
    handwritten signature is sensitive, so it must never sit plaintext in the
    DB file. Existing rows are migrated automatically on startup.
    """
    __tablename__ = "signatures"

    id = Column(String, primary_key=True, index=True)
    owner = Column(String, nullable=True, index=True)
    name = Column(String, nullable=False, default="Signature")
    data_png = Column(EncryptedText, nullable=False)   # base64 PNG, encrypted at rest
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    svg = Column(EncryptedText, nullable=True)         # vector signature, encrypted at rest



