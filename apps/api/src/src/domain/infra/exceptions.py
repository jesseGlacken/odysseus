# src/domain/infra/exceptions.py
"""Backward-compatible shim — the single source of truth is core/exceptions.py.

Moved from src/exceptions.py to src/domain/infra/exceptions.py (ODY-19 / P2.2).
Historically this module was a byte-for-byte duplicate of core/exceptions.py,
which is the canonical definition (imported by app.py, core/__init__.py, and
routes/chat_routes.py). To kill the drift, this now simply re-exports the
exception classes from core.exceptions so there is exactly one place that
defines them. Existing `from src.exceptions import ...` callers keep working.
"""
from core.exceptions import (  # noqa: F401
    SessionNotFoundError,
    InvalidFileUploadError,
    LLMServiceError,
    WebSearchError,
)

__all__ = [
    "SessionNotFoundError",
    "InvalidFileUploadError",
    "LLMServiceError",
    "WebSearchError",
]
