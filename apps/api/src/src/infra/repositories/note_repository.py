"""src.infra.repositories.note_repository — Repository for the Note aggregate (ODY-71 / P2.3b).
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy.orm import Session as DbSession

from core.database import Note
from src.infra.repositories.base import Repository


class NoteRepository(Repository[Note]):
    def __init__(self, db: DbSession) -> None:
        self._db = db

    def get(self, id: str) -> Optional[Note]:
        return self._db.query(Note).filter(Note.id == id).first()

    def list(self, **filters: Any) -> list[Note]:  # noqa: A003
        allowed = {"owner", "pinned"}
        unknown = set(filters) - allowed
        if unknown:
            raise TypeError(f"NoteRepository.list() unsupported filters: {sorted(unknown)}")
        q = self._db.query(Note)
        if "owner" in filters:
            q = q.filter(Note.owner == filters["owner"])
        if "pinned" in filters:
            q = q.filter(Note.pinned == bool(filters["pinned"]))
        return list(q.order_by(Note.updated_at.desc()).all())

    def save(self, entity: Note) -> Note:
        if not entity.id:
            entity.id = str(uuid.uuid4())
        merged: Note = self._db.merge(entity)
        self._db.flush()
        self._db.refresh(merged)
        return merged

    def delete(self, id: str) -> bool:
        n: int = self._db.query(Note).filter(Note.id == id).delete(synchronize_session="fetch")
        self._db.flush()
        return n > 0

    def list_by_user(self, username: str) -> list[Note]:
        return self.list(owner=username)
