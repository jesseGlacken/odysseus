"""src.infra.repositories — abstract repository layer (ODY-20 / P2.3).

Dependency Inversion Principle: domain code and route handlers depend on the
repository interfaces defined here, not on ``core.database`` or
``core.auth`` directly.

Quick-start (FastAPI routes)
----------------------------
Session repository::

    from fastapi import Depends
    from src.infra.repositories import SessionRepository, get_session_repo

    @router.get("/sessions/{id}")
    def get_session(
        id: str,
        repo: SessionRepository = Depends(get_session_repo),
    ):
        return repo.get(id) or HTTPException(404)

User repository::

    from src.infra.repositories import UserRepository, get_user_repo

    @router.get("/users/{username}")
    def get_user(
        username: str,
        repo: UserRepository = Depends(get_user_repo),
    ):
        return repo.get(username) or HTTPException(404)
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from src.infra.repositories.base import Repository
from src.infra.repositories.session_repository import SessionRepository
from src.infra.repositories.user_repository import UserRecord, UserRepository

__all__ = [
    # Abstract base
    "Repository",
    # Concrete repositories
    "SessionRepository",
    "UserRepository",
    # Value objects
    "UserRecord",
    # FastAPI dependency factories
    "get_session_repo",
    "get_user_repo",
]

if TYPE_CHECKING:
    from sqlalchemy.orm import Session as DbSession

# ---------------------------------------------------------------------------
# Lazy singleton: AuthManager is expensive to construct (reads auth.json).
# ---------------------------------------------------------------------------
_auth_manager_singleton: Optional[object] = None


def _get_auth_manager() -> object:
    """Return the application-wide ``AuthManager`` singleton (lazy init)."""
    global _auth_manager_singleton
    if _auth_manager_singleton is None:
        from core.auth import AuthManager
        from src.constants import AUTH_FILE

        _auth_manager_singleton = AuthManager(auth_path=AUTH_FILE)
    return _auth_manager_singleton


# ---------------------------------------------------------------------------
# FastAPI dependency factories
# ---------------------------------------------------------------------------

def get_user_repo() -> UserRepository:
    """FastAPI dependency: return a :class:`UserRepository` backed by the app
    ``AuthManager``.

    Usage::

        Depends(get_user_repo)
    """
    return UserRepository(_get_auth_manager())


def get_session_repo(
    db: "DbSession",
) -> SessionRepository:
    """FastAPI dependency: return a :class:`SessionRepository` for *db*.

    Because this function accepts a SQLAlchemy session, wire it as::

        from fastapi import Depends
        from core.database import get_db
        from src.infra.repositories import SessionRepository

        def _session_repo(db=Depends(get_db)):
            return SessionRepository(db)

        @router.get("/sessions")
        def route(repo: SessionRepository = Depends(_session_repo)):
            ...

    Or simply construct directly in a helper::

        repo = SessionRepository(db)
    """
    return SessionRepository(db)
