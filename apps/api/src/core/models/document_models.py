"""core.models.document_models — Document and DocumentVersion ORM models (ODY-21 / P2.5).

Extracted from core/database.py. Backward-compat shim in ``core.database``
re-exports both classes so ``from core.database import Document, DocumentVersion``
continues to work for all existing importers.
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
    Index,
)
from sqlalchemy.orm import relationship, backref

from core.base import Base, EncryptedText, TimestampMixin, utcnow_naive


class Document(TimestampMixin, Base):
    """Living document that the AI can create and edit in-place."""
    __tablename__ = "documents"

    id              = Column(String, primary_key=True, index=True)
    session_id      = Column(String, ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True, index=True)
    title           = Column(String, nullable=False, default="Untitled")
    language        = Column(String, nullable=True)          # "python", "markdown", "text", etc.
    current_content = Column(Text, nullable=False, default="")
    version_count   = Column(Integer, default=1)
    is_active       = Column(Boolean, default=True)
    # Soft-archive: hidden from the Library's Documents list/search/Tidy until
    # restored. Distinct from is_active (which tracks "open in a session").
    archived        = Column(Boolean, default=False)
    # Owner of this document. Documents used to derive ownership from their
    # linked chat session, but a session can be deleted (session_id → NULL via
    # SET NULL), orphaning the doc and making it vanish from the owner's
    # Library + search. Owning the row directly is robust against that.
    owner           = Column(String, nullable=True, index=True)
    tidy_verdict    = Column(String, nullable=True)        # "keep", "junk", or None (not yet reviewed)
    # Provenance: if this document was created by opening an email attachment,
    # these point back to the source email so the "Sign and reply" flow can
    # thread a response on the original conversation.
    source_email_uid         = Column(String, nullable=True)
    source_email_folder      = Column(String, nullable=True)
    source_email_account_id  = Column(String, nullable=True)
    source_email_message_id  = Column(String, nullable=True, index=True)

    session  = relationship("Session", backref=backref("documents", cascade="save-update, merge"))
    versions = relationship("DocumentVersion", back_populates="document",
                           cascade="all, delete-orphan", order_by="DocumentVersion.version_number")


class DocumentVersion(Base):
    """Immutable snapshot of a document at a point in time."""
    __tablename__ = "document_versions"

    id             = Column(String, primary_key=True, index=True)
    document_id    = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    content        = Column(Text, nullable=False)
    summary        = Column(String, nullable=True)     # Edit description
    source         = Column(String, default="ai")      # "ai" or "user"
    created_at     = Column(DateTime, default=utcnow_naive)

    document = relationship("Document", back_populates="versions")
