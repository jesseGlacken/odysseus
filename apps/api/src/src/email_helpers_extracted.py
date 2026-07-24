"""Extracted from routes/email_helpers.py for ODY-72 (P2.4b).

These functions were imported by src/ modules from routes/, violating the ADR-0001
layering rule (domain/infra code must not import from routes/).  This module acts
as an extraction shim — the actual function bodies still live in routes/email_helpers.py
for now, but src/ consumers import from here.  A follow-up (P2.2 or later) will move
the function bodies into this module and leave re-export shims in routes/.
"""
from routes.email_helpers import (  # noqa: F401 — extracted, re-exported
    SCHEDULED_DB,
    _decode_header,
    _email_cache_owner_clause,
    _extract_reply,
    _extract_text,
    _get_email_config,
    _imap_connect,
    _init_scheduled_db,
    _list_email_accounts,
    _send_smtp_message,
    email_translation_body_hash,
)
