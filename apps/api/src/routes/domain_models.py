"""Pydantic v2 response models for remaining domains (P1.3e).

Covers: calendar, notes, session, prefs/settings, gallery, cookbook,
research, memory, history.
"""

from pydantic import BaseModel, Field


# ── Calendar ────────────────────────────────────────────────────────────────

class CalendarEventResponse(BaseModel):
    id: str = Field(default="", description="Event ID")
    title: str = Field(default="", description="Event title")
    start: str = Field(default="", description="Start time ISO")
    end: str = Field(default="", description="End time ISO")
    description: str = Field(default="", description="Event description")
    location: str = Field(default="", description="Event location")
    all_day: bool = Field(default=False)
    calendar_name: str = Field(default="")
    color: str = Field(default="")


class CalendarStatusResponse(BaseModel):
    ok: bool = Field(..., description="Whether the operation succeeded")
    message: str = Field(default="")


# ── Notes ───────────────────────────────────────────────────────────────────

class NoteResponse(BaseModel):
    id: str = Field(default="")
    title: str = Field(default="")
    content: str = Field(default="")
    created_at: str = Field(default="")
    updated_at: str = Field(default="")
    due_date: str | None = Field(default=None)
    pinned: bool = Field(default=False)


class NoteStatusResponse(BaseModel):
    ok: bool = Field(...)
    message: str = Field(default="")


# ── Session ─────────────────────────────────────────────────────────────────

class SessionResponse(BaseModel):
    id: str = Field(default="")
    name: str = Field(default="")
    created_at: str = Field(default="")
    updated_at: str = Field(default="")
    owner: str = Field(default="")
    archived: bool = Field(default=False)
    model: str = Field(default="")


class SessionListResponse(BaseModel):
    sessions: list[dict] = Field(default_factory=list)


# ── Prefs / Settings ────────────────────────────────────────────────────────

class PrefsResponse(BaseModel):
    ok: bool = Field(...)
    settings: dict = Field(default_factory=dict)


class ThemeResponse(BaseModel):
    ok: bool = Field(...)
    theme: dict = Field(default_factory=dict)


# ── Gallery ─────────────────────────────────────────────────────────────────

class GalleryImageResponse(BaseModel):
    id: str = Field(default="")
    filename: str = Field(default="")
    url: str = Field(default="")
    thumbnail_url: str = Field(default="")
    width: int = Field(default=0)
    height: int = Field(default=0)
    created_at: str = Field(default="")


class GalleryListResponse(BaseModel):
    images: list[dict] = Field(default_factory=list)


# ── Cookbook ────────────────────────────────────────────────────────────────

class CookbookStatusResponse(BaseModel):
    ok: bool = Field(...)
    message: str = Field(default="")
    state: str = Field(default="")


# ── Research ────────────────────────────────────────────────────────────────

class ResearchStatusResponse(BaseModel):
    ok: bool = Field(...)
    status: str = Field(default="")
    report_id: str = Field(default="")


# ── Memory ──────────────────────────────────────────────────────────────────

class MemoryEntryResponse(BaseModel):
    id: str = Field(default="")
    content: str = Field(default="")
    category: str = Field(default="")
    created_at: str = Field(default="")


class MemoryListResponse(BaseModel):
    entries: list[dict] = Field(default_factory=list)
    total: int = Field(default=0)


# ── History ─────────────────────────────────────────────────────────────────

class HistoryStatusResponse(BaseModel):
    ok: bool = Field(...)
