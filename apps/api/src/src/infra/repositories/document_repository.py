"""src.infra.repositories.document_repository — Repository for the Document aggregate (ODY-71 / P2.3b).
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy.orm import Session as DbSession

from core.models.document_models import Document
from src.infra.repositories.base import Repository


class DocumentRepository(Repository[Document]):
    def __init__(self, db: DbSession) -> None:
        self._db = db

    def get(self, id: str) -> Optional[Document]:
        return self._db.query(Document).filter(Document.id == id).first()

    def list(self, **filters: Any) -> list[Document]:  # noqa: A003
        allowed = {"owner", "archived", "is_active"}
        unknown = set(filters) - allowed
        if unknown:
            raise TypeError(f"DocumentRepository.list() unsupported filters: {sorted(unknown)}")
        q = self._db.query(Document)
        if "owner" in filters:
            q = q.filter(Document.owner == filters["owner"])
        if "archived" in filters:
            q = q.filter(Document.archived == bool(filters["archived"]))
        if "is_active" in filters:
            q = q.filter(Document.is_active == bool(filters["is_active"]))
        return list(q.order_by(Document.updated_at.desc()).all())

    def save(self, entity: Document) -> Document:
        if not entity.id:
            entity.id = str(uuid.uuid4())
        merged: Document = self._db.merge(entity)
        self._db.flush()
        self._db.refresh(merged)
        return merged

    def delete(self, id: str) -> bool:
        n: int = self._db.query(Document).filter(Document.id == id).delete(synchronize_session="fetch")
        self._db.flush()
        return n > 0

    def list_by_user(self, username: str) -> list[Document]:
        return self.list(owner=username)
