"""core.base — shared SQLAlchemy infrastructure (ODY-21 / P2.5).

Extracted from core.database to break circular imports between model files
and the main database module.  Model files import from here; database.py
imports from here as well.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.types import TypeDecorator, Text

Base = declarative_base()


def utcnow_naive() -> datetime:
    """Return naive UTC for existing DateTime columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class TimestampMixin:
    """Mixin that adds timestamp fields to models."""
    @declared_attr
    def created_at(cls):
        return Column(DateTime, default=utcnow_naive, nullable=False)

    @declared_attr
    def updated_at(cls):
        return Column(DateTime, default=utcnow_naive, onupdate=utcnow_naive, nullable=False)


class EncryptedText(TypeDecorator):
    """Text column transparently encrypted at rest via src.secret_storage.

    Writes are Fernet-encrypted (``enc:`` prefix); reads decrypt back to
    plaintext.  Legacy plaintext rows pass through unchanged until their next
    write (a startup migration encrypts them).
    """
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        from src.secret_storage import encrypt
        return encrypt(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        from src.secret_storage import decrypt
        return decrypt(value)
