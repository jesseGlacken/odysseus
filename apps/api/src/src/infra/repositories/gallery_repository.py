"""src.infra.repositories.gallery_repository — Repository for Gallery aggregates (ODY-71 / P2.3b).
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy.orm import Session as DbSession

from core.database import GalleryAlbum, GalleryImage
from src.infra.repositories.base import Repository


class GalleryRepository(Repository[GalleryAlbum]):
    """Repository for gallery albums and images."""

    def __init__(self, db: DbSession) -> None:
        self._db = db

    def get(self, id: str) -> Optional[GalleryAlbum]:
        return self._db.query(GalleryAlbum).filter(GalleryAlbum.id == id).first()

    def list(self, **filters: Any) -> list[GalleryAlbum]:  # noqa: A003
        allowed = {"owner"}
        unknown = set(filters) - allowed
        if unknown:
            raise TypeError(f"GalleryRepository.list() unsupported filters: {sorted(unknown)}")
        q = self._db.query(GalleryAlbum)
        if "owner" in filters:
            q = q.filter(GalleryAlbum.owner == filters["owner"])
        return list(q.order_by(GalleryAlbum.created_at.desc()).all())

    def save(self, entity: GalleryAlbum) -> GalleryAlbum:
        if not entity.id:
            entity.id = str(uuid.uuid4())
        merged: GalleryAlbum = self._db.merge(entity)
        self._db.flush()
        self._db.refresh(merged)
        return merged

    def delete(self, id: str) -> bool:
        n: int = self._db.query(GalleryAlbum).filter(GalleryAlbum.id == id).delete(synchronize_session="fetch")
        self._db.flush()
        return n > 0

    def list_by_user(self, username: str) -> list[GalleryAlbum]:
        return self.list(owner=username)

    # -- Images (child aggregate) -----------------------------------------------

    def get_image(self, id: str) -> Optional[GalleryImage]:
        return self._db.query(GalleryImage).filter(GalleryImage.id == id).first()

    def list_images(self, album_id: str) -> list[GalleryImage]:
        return list(
            self._db.query(GalleryImage)
            .filter(GalleryImage.album_id == album_id)
            .order_by(GalleryImage.created_at.desc())
            .all()
        )

    def save_image(self, entity: GalleryImage) -> GalleryImage:
        if not entity.id:
            entity.id = str(uuid.uuid4())
        merged: GalleryImage = self._db.merge(entity)
        self._db.flush()
        self._db.refresh(merged)
        return merged

    def delete_image(self, id: str) -> bool:
        n: int = self._db.query(GalleryImage).filter(GalleryImage.id == id).delete(synchronize_session="fetch")
        self._db.flush()
        return n > 0
