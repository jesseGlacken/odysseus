"""core.models — domain-specific SQLAlchemy model modules (ODY-21 / P2.5).

All 26 models are now available both via ``from core.database import <Model>``
(backward-compat) and ``from core.models import <Model>`` (new path).
The original class definitions remain in database.py during the transition.

Usage::

    # SQLAlchemy models
    from core.models import GalleryAlbum, ModelEndpoint, ScheduledTask
    from core.models import Memory, Note, CalendarCal, Integration

    # Dataclass models (public API)
    from core.models import Session, ChatMessage
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

# SQLAlchemy models — previously extracted (ODY-21)
from core.models.session_models import Session as DbSession, ChatMessage as DbChatMessage
from core.models.document_models import Document, DocumentVersion
from core.models.email_models import EmailAccount

# SQLAlchemy models — extracted in ODY-73 (P2.5b)
from core.models.calendar_models import CalendarCal, CalendarDeletedEvent, CalendarEvent
from core.models.comparison_models import Comparison, Signature
from core.models.crew_models import CrewMember
from core.models.gallery_models import GalleryAlbum, GalleryImage
from core.models.integration_models import Integration
from core.models.memory_models import Memory
from core.models.model_models import McpServer, ModelEndpoint, ProviderAuthSession
from core.models.note_models import Note
from core.models.task_models import EditorDraft, ScheduledTask, TaskRun
from core.models.token_models import ApiToken, Webhook
from core.models.tool_models import UserTool, UserToolData

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
    # SQLAlchemy models (ODY-21)
    "DbSession",
    "DbChatMessage",
    "Document",
    "DocumentVersion",
    "EmailAccount",
    # SQLAlchemy models (ODY-73)
    "ApiToken",
    "CalendarCal",
    "CalendarDeletedEvent",
    "CalendarEvent",
    "Comparison",
    "CrewMember",
    "EditorDraft",
    "GalleryAlbum",
    "GalleryImage",
    "Integration",
    "McpServer",
    "Memory",
    "ModelEndpoint",
    "Note",
    "ProviderAuthSession",
    "ScheduledTask",
    "Signature",
    "TaskRun",
    "UserTool",
    "UserToolData",
    "Webhook",
    # Dataclass models (public API — session_manager depends on these)
    "Session",
    "ChatMessage",
    # Session manager singleton
    "set_session_manager_instance",
    "get_session_manager_instance",
    "set_session_manager",
    "get_session_manager",
]
