"""src.infra.repositories.chat_message_repository — Repository for the ChatMessage aggregate (ODY-71 / P2.3b).
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy.orm import Session as DbSession

from core.models.session_models import ChatMessage
from src.infra.repositories.base import Repository


class ChatMessageRepository(Repository[ChatMessage]):
    def __init__(self, db: DbSession) -> None:
        self._db = db

    def get(self, id: str) -> Optional[ChatMessage]:
        return self._db.query(ChatMessage).filter(ChatMessage.id == id).first()

    def list(self, **filters: Any) -> list[ChatMessage]:  # noqa: A003
        allowed = {"session_id"}
        unknown = set(filters) - allowed
        if unknown:
            raise TypeError(f"ChatMessageRepository.list() unsupported filters: {sorted(unknown)}")
        q = self._db.query(ChatMessage)
        if "session_id" in filters:
            q = q.filter(ChatMessage.session_id == filters["session_id"])
        return list(q.order_by(ChatMessage.timestamp.asc()).all())

    def save(self, entity: ChatMessage) -> ChatMessage:
        if not entity.id:
            entity.id = str(uuid.uuid4())
        merged: ChatMessage = self._db.merge(entity)
        self._db.flush()
        self._db.refresh(merged)
        return merged

    def delete(self, id: str) -> bool:
        n: int = self._db.query(ChatMessage).filter(ChatMessage.id == id).delete(synchronize_session="fetch")
        self._db.flush()
        return n > 0

    def list_by_session(self, session_id: str) -> list[ChatMessage]:
        return self.list(session_id=session_id)
