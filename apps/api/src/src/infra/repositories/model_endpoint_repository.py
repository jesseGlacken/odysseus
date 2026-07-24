"""src.infra.repositories.model_endpoint_repository — Repository for ModelEndpoint (ODY-71 / P2.3b).
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy.orm import Session as DbSession

from core.database import ModelEndpoint
from src.infra.repositories.base import Repository


class ModelEndpointRepository(Repository[ModelEndpoint]):
    def __init__(self, db: DbSession) -> None:
        self._db = db

    def get(self, id: str) -> Optional[ModelEndpoint]:
        return self._db.query(ModelEndpoint).filter(ModelEndpoint.id == id).first()

    def list(self, **filters: Any) -> list[ModelEndpoint]:  # noqa: A003
        allowed = {"is_enabled"}
        unknown = set(filters) - allowed
        if unknown:
            raise TypeError(f"ModelEndpointRepository.list() unsupported filters: {sorted(unknown)}")
        q = self._db.query(ModelEndpoint)
        if "is_enabled" in filters:
            q = q.filter(ModelEndpoint.is_enabled == bool(filters["is_enabled"]))
        return list(q.order_by(ModelEndpoint.created_at.desc()).all())

    def save(self, entity: ModelEndpoint) -> ModelEndpoint:
        if not entity.id:
            entity.id = str(uuid.uuid4())
        merged: ModelEndpoint = self._db.merge(entity)
        self._db.flush()
        self._db.refresh(merged)
        return merged

    def delete(self, id: str) -> bool:
        n: int = self._db.query(ModelEndpoint).filter(ModelEndpoint.id == id).delete(synchronize_session="fetch")
        self._db.flush()
        return n > 0

    def get_by_name(self, name: str) -> Optional[ModelEndpoint]:
        return self._db.query(ModelEndpoint).filter(ModelEndpoint.name == name).first()
