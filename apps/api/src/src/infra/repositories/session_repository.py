"""src.infra.repositories.session_repository — Repository for chat Session aggregate (ODY-20 / P2.3).

Chat sessions (``core.database.Session``) are the primary user-facing
aggregate in Odysseus.  This repository wraps a SQLAlchemy database session
and exposes typed, testable methods that callers can use without knowing
about SQLAlchemy directly.

The ``Session`` *SQLAlchemy model* is imported as ``ChatSession`` to avoid
shadowing the SQLAlchemy ``Session`` *database-connection* type used in the
constructor parameter.

Usage with FastAPI
------------------
Wire via the helper in ``src.infra.repositories``::

    from fastapi import Depends
    from core.database import get_db
    from src.infra.repositories import SessionRepository

    def _session_repo(db=Depends(get_db)) -> SessionRepository:
        return SessionRepository(db)

    @router.get("/sessions/{id}")
    def route(id: str, repo: SessionRepository = Depends(_session_repo)):
        return repo.get(id)
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy.orm import Session as DbSession

# ``Session`` in core.database is the ORM model for chat sessions.
# Alias to prevent shadowing the SQLAlchemy Session type above.
from core.database import Session as ChatSession
from core.database import utcnow_naive
from src.infra.repositories.base import Repository


class SessionRepository(Repository[ChatSession]):
    """Repository for the chat ``Session`` aggregate.

    Parameters
    ----------
    db:
        A SQLAlchemy ``Session`` (database connection) provided by
        ``core.database.get_db`` or a test fixture.  The repository does
        **not** commit or roll back — that is the caller's responsibility.
        Methods call ``flush()`` so that returned objects reflect the latest
        state within the current transaction.
    """

    def __init__(self, db: DbSession) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Repository[ChatSession] interface
    # ------------------------------------------------------------------

    def get(self, id: str) -> Optional[ChatSession]:
        """Return the chat session with *id*, or ``None`` if not found."""
        return (
            self._db.query(ChatSession)
            .filter(ChatSession.id == id)
            .first()
        )

    def list(self, **filters: Any) -> list[ChatSession]:  # noqa: A003
        """Return chat sessions matching *filters*.

        Supported filter keys
        ----------------------
        owner : str
            Return only sessions whose ``owner`` field equals this value.
        archived : bool
            ``True`` returns only archived sessions; ``False`` returns only
            active ones.  Omit to return sessions regardless of state.

        Results are ordered by ``last_accessed`` descending (newest first).

        Raises
        ------
        TypeError:
            If an unrecognised filter key is passed.
        """
        allowed = {"owner", "archived"}
        unknown = set(filters) - allowed
        if unknown:
            raise TypeError(
                f"SessionRepository.list() does not support filter(s): {sorted(unknown)}"
            )

        q = self._db.query(ChatSession)
        if "owner" in filters:
            q = q.filter(ChatSession.owner == filters["owner"])
        if "archived" in filters:
            q = q.filter(ChatSession.archived == bool(filters["archived"]))
        return list(q.order_by(ChatSession.last_accessed.desc()).all())

    def save(self, entity: ChatSession) -> ChatSession:
        """Persist *entity* (insert or update) and return the refreshed instance.

        If *entity.id* is falsy a new UUID4 is assigned before the merge.
        The returned object is the entity refreshed from the database so
        server-side defaults (e.g. ``created_at``) are populated.

        Parameters
        ----------
        entity:
            A ``ChatSession`` ORM instance.  May be transient (new) or
            detached (previously loaded, then modified).
        """
        if not entity.id:
            entity.id = str(uuid.uuid4())
        merged: ChatSession = self._db.merge(entity)
        self._db.flush()
        self._db.refresh(merged)
        return merged

    def delete(self, id: str) -> bool:
        """Delete the chat session with *id*.

        Also removes all associated ``ChatMessage`` rows via the
        ``cascade="all, delete-orphan"`` relationship on the model.

        Returns ``True`` if the session existed and was deleted, ``False``
        if it was not found (idempotent — never raises on a missing id).
        """
        n: int = (
            self._db.query(ChatSession)
            .filter(ChatSession.id == id)
            .delete(synchronize_session="fetch")
        )
        self._db.flush()
        return n > 0

    # ------------------------------------------------------------------
    # Domain-specific helpers
    # ------------------------------------------------------------------

    def list_by_user(self, username: str) -> list[ChatSession]:
        """Return all sessions owned by *username*, newest-first.

        Includes both active and archived sessions.  Use :meth:`get_active`
        to restrict to non-archived sessions only.
        """
        return self.list(owner=username)

    def get_active(self, username: str) -> list[ChatSession]:
        """Return the non-archived sessions owned by *username*, newest-first."""
        return self.list(owner=username, archived=False)

    def archive(self, id: str) -> bool:
        """Mark session *id* as archived.

        Uses a single ``UPDATE`` query — more efficient than a fetch + modify
        cycle and avoids SQLAlchemy attribute-assignment type ambiguity.

        Returns ``True`` if the session was found and updated, ``False``
        otherwise.
        """
        n: int = (
            self._db.query(ChatSession)
            .filter(ChatSession.id == id)
            .update({"archived": True}, synchronize_session="fetch")
        )
        self._db.flush()
        return n > 0

    def touch(self, id: str) -> bool:
        """Update ``last_accessed`` for session *id* to the current UTC time.

        Uses a single ``UPDATE`` query for the same reasons as :meth:`archive`.

        Returns ``True`` if the session was found, ``False`` otherwise.
        """
        n: int = (
            self._db.query(ChatSession)
            .filter(ChatSession.id == id)
            .update({"last_accessed": utcnow_naive()}, synchronize_session="fetch")
        )
        self._db.flush()
        return n > 0
