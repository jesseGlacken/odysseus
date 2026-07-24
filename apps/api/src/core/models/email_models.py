"""core.models.email_models — EmailAccount ORM model (ODY-21 / P2.5).

Extracted from core/database.py. Backward-compat shim in ``core.database``
re-exports EmailAccount so ``from core.database import EmailAccount`` still
works for all existing importers.
"""
from __future__ import annotations

from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    Index,
)

from core.base import Base, EncryptedText, TimestampMixin


class EmailAccount(TimestampMixin, Base):
    """A configured IMAP/SMTP account. Supports multiple accounts per user —
    exactly one row per owner has is_default=True.

    Security note: imap_password / smtp_password are stored Fernet-encrypted
    via src/secret_storage.py. The key lives at data/.app_key (mode 0o600,
    gitignored). Anyone with read access to that file can decrypt every
    row, so the threat model is "stolen SQLite backup" rather than
    "process compromise". On first start any legacy plaintext rows are
    migrated automatically (see _migrate_encrypt_email_passwords).
    """
    __tablename__ = "email_accounts"

    id             = Column(String, primary_key=True, index=True)
    owner          = Column(String, nullable=True, index=True)
    name           = Column(String, nullable=False)  # Display name: "Work", "Personal", etc.
    is_default     = Column(Boolean, default=False, nullable=False)
    enabled        = Column(Boolean, default=True, nullable=False)

    # IMAP (receiving)
    imap_host      = Column(String, default="")
    imap_port      = Column(Integer, default=993)
    imap_user      = Column(String, default="")
    imap_password  = Column(String, default="")
    imap_starttls  = Column(Boolean, default=True)

    # SMTP (sending)
    smtp_host      = Column(String, default="")
    smtp_port      = Column(Integer, default=465)
    smtp_security  = Column(String, default="ssl")  # ssl | starttls | none
    smtp_user      = Column(String, default="")
    smtp_password  = Column(String, default="")

    from_address   = Column(String, default="")
    display_name   = Column(String, nullable=True)   # "Hriday Ranka" — used in From: header

    # OAuth2 (Google / Google Workspace). Tokens stored encrypted via secret_storage.
    oauth_provider      = Column(String, nullable=True)   # "google" or None
    oauth_access_token  = Column(String, nullable=True)   # encrypted
    oauth_refresh_token = Column(String, nullable=True)   # encrypted
    oauth_token_expiry  = Column(String, nullable=True)   # unix timestamp string

    __table_args__ = (
        Index('ix_email_accounts_owner_default', 'owner', 'is_default'),
    )
