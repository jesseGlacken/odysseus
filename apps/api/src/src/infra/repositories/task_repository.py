"""src.infra.repositories.task_repository — Repository for ScheduledTask/TaskRun aggregates (ODY-71 / P2.3b).
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy.orm import Session as DbSession

from core.database import ScheduledTask, TaskRun
from src.infra.repositories.base import Repository


class TaskRepository(Repository[ScheduledTask]):
    """Repository for scheduled tasks and their run history."""

    def __init__(self, db: DbSession) -> None:
        self._db = db

    def get(self, id: str) -> Optional[ScheduledTask]:
        return self._db.query(ScheduledTask).filter(ScheduledTask.id == id).first()

    def list(self, **filters: Any) -> list[ScheduledTask]:  # noqa: A003
        allowed = {"owner", "status"}
        unknown = set(filters) - allowed
        if unknown:
            raise TypeError(f"TaskRepository.list() unsupported filters: {sorted(unknown)}")
        q = self._db.query(ScheduledTask)
        if "owner" in filters:
            q = q.filter(ScheduledTask.owner == filters["owner"])
        if "status" in filters:
            q = q.filter(ScheduledTask.status == filters["status"])
        return list(q.order_by(ScheduledTask.created_at.desc()).all())

    def save(self, entity: ScheduledTask) -> ScheduledTask:
        if not entity.id:
            entity.id = str(uuid.uuid4())
        merged: ScheduledTask = self._db.merge(entity)
        self._db.flush()
        self._db.refresh(merged)
        return merged

    def delete(self, id: str) -> bool:
        n: int = self._db.query(ScheduledTask).filter(ScheduledTask.id == id).delete(synchronize_session="fetch")
        self._db.flush()
        return n > 0

    def list_by_user(self, username: str) -> list[ScheduledTask]:
        return self.list(owner=username)

    # -- Task runs ---------------------------------------------------------------

    def get_run(self, id: str) -> Optional[TaskRun]:
        return self._db.query(TaskRun).filter(TaskRun.id == id).first()

    def list_runs(self, task_id: str) -> list[TaskRun]:
        return list(
            self._db.query(TaskRun)
            .filter(TaskRun.task_id == task_id)
            .order_by(TaskRun.last_run.desc())
            .all()
        )

    def save_run(self, entity: TaskRun) -> TaskRun:
        if not entity.id:
            entity.id = str(uuid.uuid4())
        merged: TaskRun = self._db.merge(entity)
        self._db.flush()
        self._db.refresh(merged)
        return merged

    def delete_runs_for_task(self, task_id: str) -> int:
        n: int = self._db.query(TaskRun).filter(TaskRun.task_id == task_id).delete(synchronize_session="fetch")
        self._db.flush()
        return n
