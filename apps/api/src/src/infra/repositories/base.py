"""src.infra.repositories.base — abstract Repository[T] interface (ODY-20 / P2.3).

Dependency Inversion Principle: domain code depends on this abstraction, not
on SQLAlchemy sessions or file I/O directly.  Concrete implementations live in
the sibling modules (session_repository, user_repository, …).

All methods are synchronous to match the current sync-SQLAlchemy stack; the
interface is intentionally thin so a future async migration can swap
implementations without touching callers.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, Optional, TypeVar

T = TypeVar("T")


class Repository(ABC, Generic[T]):
    """Abstract repository interface for domain entities.

    Each concrete subclass is responsible for exactly one aggregate root (e.g.
    ``Session``, ``UserRecord``).  Callers receive instances via FastAPI
    ``Depends()`` factories defined in ``src.infra.repositories``.

    Parameters
    ----------
    T:
        The aggregate-root type this repository manages.
    """

    @abstractmethod
    def get(self, id: str) -> Optional[T]:
        """Return the entity identified by *id*, or ``None`` if not found."""
        ...

    @abstractmethod
    def list(self, **filters: Any) -> list[T]:
        """Return entities matching *filters*.

        An empty *filters* dict means "no filter" — return all entities owned
        by or visible to the current tenant context.  Concrete subclasses
        document the supported filter keys.
        """
        ...

    @abstractmethod
    def save(self, entity: T) -> T:
        """Persist *entity* (insert or update) and return the stored copy.

        For ORM-backed repositories the returned object is the same instance
        refreshed from the database.  For JSON-backed stores it is a new
        ``frozen`` dataclass instance built from the written data.
        """
        ...

    @abstractmethod
    def delete(self, id: str) -> bool:
        """Remove the entity identified by *id*.

        Returns ``True`` if the entity existed and was deleted, ``False`` if it
        was not found (idempotent — never raises on missing).
        """
        ...
