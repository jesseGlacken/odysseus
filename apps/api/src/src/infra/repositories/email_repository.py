"""src.infra.repositories.email_repository — Repository for the EmailAccount aggregate (ODY-71 / P2.3b).
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy.orm import Session as DbSession

from core.models.email_models import EmailAccount
from src.infra.repositories.base import Repository


class EmailRepository(Repository[EmailAccount]):
    def __init__(self, db: DbSession) -> None:
        self._db = db

    def get(self, id: str) -> Optional[EmailAccount]:
        return self._db.query(EmailAccount).filter(EmailAccount.id == id).first()

    def list(self, **filters: Any) -> list[EmailAccount]:  # noqa: A003
        allowed = {"owner", "is_default"}
        unknown = set(filters) - allowed
        if unknown:
            raise TypeError(f"EmailRepository.list() unsupported filters: {sorted(unknown)}")
        q = self._db.query(EmailAccount)
        if "owner" in filters:
            q = q.filter(EmailAccount.owner == filters["owner"])
        if "is_default" in filters:
            q = q.filter(EmailAccount.is_default == bool(filters["is_default"]))
        return list(q.order_by(EmailAccount.created_at.desc()).all())

    def save(self, entity: EmailAccount) -> EmailAccount:
        if not entity.id:
            entity.id = str(uuid.uuid4())
        merged: EmailAccount = self._db.merge(entity)
        self._db.flush()
        self._db.refresh(merged)
        return merged

    def delete(self, id: str) -> bool:
        n: int = self._db.query(EmailAccount).filter(EmailAccount.id == id).delete(synchronize_session="fetch")
        self._db.flush()
        return n > 0

    def list_by_user(self, username: str) -> list[EmailAccount]:
        return self.list(owner=username)
