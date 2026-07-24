"""src.infra.repositories.calendar_repository — Repository for Calendar aggregates (ODY-71 / P2.3b).
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy.orm import Session as DbSession

from core.database import CalendarCal, CalendarEvent
from src.infra.repositories.base import Repository


class CalendarRepository(Repository[CalendarCal]):
    """Repository for calendars and their events."""

    def __init__(self, db: DbSession) -> None:
        self._db = db

    def get(self, id: str) -> Optional[CalendarCal]:
        return self._db.query(CalendarCal).filter(CalendarCal.id == id).first()

    def list(self, **filters: Any) -> list[CalendarCal]:  # noqa: A003
        allowed = {"owner"}
        unknown = set(filters) - allowed
        if unknown:
            raise TypeError(f"CalendarRepository.list() unsupported filters: {sorted(unknown)}")
        q = self._db.query(CalendarCal)
        if "owner" in filters:
            q = q.filter(CalendarCal.owner == filters["owner"])
        return list(q.order_by(CalendarCal.created_at.desc()).all())

    def save(self, entity: CalendarCal) -> CalendarCal:
        if not entity.id:
            entity.id = str(uuid.uuid4())
        merged: CalendarCal = self._db.merge(entity)
        self._db.flush()
        self._db.refresh(merged)
        return merged

    def delete(self, id: str) -> bool:
        n: int = self._db.query(CalendarCal).filter(CalendarCal.id == id).delete(synchronize_session="fetch")
        self._db.flush()
        return n > 0

    def list_by_user(self, username: str) -> list[CalendarCal]:
        return self.list(owner=username)

    # -- Events (child aggregate) -------------------------------------------------

    def get_event(self, uid: str) -> Optional[CalendarEvent]:
        return self._db.query(CalendarEvent).filter(CalendarEvent.uid == uid).first()

    def list_events(self, calendar_id: str) -> list[CalendarEvent]:
        return list(
            self._db.query(CalendarEvent)
            .filter(CalendarEvent.calendar_id == calendar_id)
            .order_by(CalendarEvent.dtstart.asc())
            .all()
        )

    def save_event(self, entity: CalendarEvent) -> CalendarEvent:
        if not entity.uid:
            entity.uid = str(uuid.uuid4())
        merged: CalendarEvent = self._db.merge(entity)
        self._db.flush()
        self._db.refresh(merged)
        return merged

    def delete_event(self, uid: str) -> bool:
        n: int = self._db.query(CalendarEvent).filter(CalendarEvent.uid == uid).delete(synchronize_session="fetch")
        self._db.flush()
        return n > 0
