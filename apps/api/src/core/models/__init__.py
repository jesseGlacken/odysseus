"""core.models — domain-specific SQLAlchemy model modules (ODY-21 / P2.5).

Seed extraction (this PR): Session, ChatMessage, Document, DocumentVersion,
EmailAccount have been moved to their own SQLAlchemy model files.
All 26 models remain accessible via ``from core.database import <Model>``
(backward-compat shims kept in database.py).

Remaining 21 models are still defined in core/database.py and will be
extracted in follow-up tickets (ODY-21b).

Usage::

    # Dataclass models (public API — session_manager depends on these)
    from core.models import Session, ChatMessage

    # SQLAlchemy models (via submodule or Db-prefixed alias)
    from core.models.session_models import Session  # SQLAlchemy
    from core.models import DbSession, DbChatMessage  # SQLAlchemy aliases

    # Domain models
    from core.models import Document, DocumentVersion
    from core.models import EmailAccount
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

# SQLAlchemy models — import with Db prefix to avoid conflict with dataclasses
from core.models.session_models import Session as DbSession, ChatMessage as DbChatMessage
from core.models.document_models import Document, DocumentVersion
from core.models.email_models import EmailAccount

# Dataclass Session/ChatMessage from the original core/models.py (now _legacy.py).
# These are the public API of core.models — session_manager depends on them.
from core.models._legacy import (
    ChatMessage,
    Session,
)

if TYPE_CHECKING:
    from core.session_manager import SessionManager


# ---------------------------------------------------------------------------
# Session manager singleton (pre-existing in core/models.py — preserved)
# ---------------------------------------------------------------------------
_SESSION_MANAGER_INSTANCE: Optional["SessionManager"] = None


def set_session_manager_instance(manager: "SessionManager"):
    """Set the global SessionManager singleton."""
    global _SESSION_MANAGER_INSTANCE
    _SESSION_MANAGER_INSTANCE = manager


def get_session_manager_instance() -> Optional["SessionManager"]:
    """Get the global SessionManager singleton."""
    return _SESSION_MANAGER_INSTANCE


# Legacy aliases
set_session_manager = set_session_manager_instance
get_session_manager = get_session_manager_instance


__all__ = [
    # SQLAlchemy models (accessible via submodule or Db-prefixed alias)
    "DbSession",
    "DbChatMessage",
    "Document",
    "DocumentVersion",
    "EmailAccount",
    # Dataclass models (public API — session_manager depends on these)
    "Session",
    "ChatMessage",
    # Session manager singleton
    "set_session_manager_instance",
    "get_session_manager_instance",
    "set_session_manager",
    "get_session_manager",
]
