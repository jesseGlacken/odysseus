"""Extracted from core/database.py for ODY-73 (P2.5b).

See ADR-0011 and the ODY-21 extraction pattern for rationale.
"""
from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Index,
)
from sqlalchemy.orm import backref, relationship

from core.base import Base, TimestampMixin
from core.base import EncryptedText, utcnow_naive


class GalleryAlbum(TimestampMixin, Base):
    """A photo album/folder."""
    __tablename__ = "gallery_albums"

    id          = Column(String, primary_key=True, index=True)
    name        = Column(String, nullable=False)
    description = Column(Text, default="")
    cover_id    = Column(String, nullable=True)  # GalleryImage.id for cover photo
    owner       = Column(String, nullable=True, index=True)

    images = relationship("GalleryImage", back_populates="album")



class GalleryImage(TimestampMixin, Base):
    """Stores metadata for photos and AI-generated images."""
    __tablename__ = "gallery_images"

    id         = Column(String, primary_key=True, index=True)
    filename   = Column(String, nullable=False, unique=True)
    prompt     = Column(Text, nullable=False, default="")
    caption    = Column(Text, nullable=True, default="")
    model      = Column(String, nullable=True)
    size       = Column(String, nullable=True)
    quality    = Column(String, nullable=True)
    tags       = Column(String, nullable=True, default="")
    ai_tags    = Column(Text, nullable=True, default="")       # AI-generated tags (comma-separated)
    session_id = Column(String, ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True, index=True)
    album_id   = Column(String, ForeignKey("gallery_albums.id", ondelete="SET NULL"), nullable=True, index=True)
    owner      = Column(String, nullable=True, index=True)
    is_active  = Column(Boolean, default=True)
    favorite   = Column(Boolean, default=False)

    # File integrity
    file_hash  = Column(String(64), nullable=True, index=True)  # SHA-256

    # EXIF / photo metadata
    taken_at       = Column(DateTime, nullable=True, index=True)  # EXIF DateTimeOriginal
    camera_make    = Column(String, nullable=True)
    camera_model   = Column(String, nullable=True)
    gps_lat        = Column(String, nullable=True)  # stored as string for precision
    gps_lng        = Column(String, nullable=True)
    width          = Column(Integer, nullable=True)
    height         = Column(Integer, nullable=True)
    file_size      = Column(Integer, nullable=True)  # bytes

    session = relationship("Session", backref=backref("gallery_images"))
    album   = relationship("GalleryAlbum", back_populates="images")

    __table_args__ = (
        Index('ix_gallery_images_tags', 'tags'),
        Index('ix_gallery_images_model', 'model'),
        Index('ix_gallery_images_active', 'is_active', 'created_at'),
    )



