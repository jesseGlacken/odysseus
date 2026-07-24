"""src.infra.repositories.memory_repository — Repository for the Memory aggregate (ODY-71 / P2.3b).
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy.orm import Session as DbSession

from core.database import Memory
from src.infra.repositories.base import Repository


class MemoryRepository(Repository[Memory]):
    def __init__(self, db: DbSession) -> None:
        self._db = db

    def get(self, id: str) -> Optional[Memory]:
        return self._db.query(Memory).filter(Memory.id == id).first()

    def list(self, **filters: Any) -> list[Memory]:  # noqa: A003
        allowed = {"owner", "category"}
        unknown = set(filters) - allowed
        if unknown:
            raise TypeError(f"MemoryRepository.list() unsupported filters: {sorted(unknown)}")
        q = self._db.query(Memory)
        if "owner" in filters:
            q = q.filter(Memory.owner == filters["owner"])
        if "category" in filters:
            q = q.filter(Memory.category == filters["category"])
        return list(q.order_by(Memory.timestamp.desc()).all())

    def save(self, entity: Memory) -> Memory:
        if not entity.id:
            entity.id = str(uuid.uuid4())
        merged: Memory = self._db.merge(entity)
        self._db.flush()
        self._db.refresh(merged)
        return merged

    def delete(self, id: str) -> bool:
        n: int = self._db.query(Memory).filter(Memory.id == id).delete(synchronize_session="fetch")
        self._db.flush()
        return n > 0

    def list_by_user(self, username: str) -> list[Memory]:
        return self.list(owner=username)
