"""Pydantic v2 request and response models for the document router.

These models are the source of truth for /api/document and /api/documents
request/response shapes. File-download endpoints (PDF, PNG, ZIP) return
FileResponse/StreamingResponse and cannot carry a typed response_model.
"""

from pydantic import BaseModel, Field


# ── Core document response ──────────────────────────────────────────────────

class DocumentResponse(BaseModel):
    """Response for single-document operations (create, get, update, etc.)."""
    id: str = Field(default="", description="Document ID")
    title: str = Field(default="", description="Document title")
    content: str = Field(default="", description="Document plain-text content")
    language: str = Field(default="", description="Document language code")
    session_id: str = Field(default="", description="Owning session ID")
    created_at: str = Field(default="", description="ISO timestamp")
    updated_at: str = Field(default="", description="ISO timestamp")
    archived: bool = Field(default=False, description="Whether the document is archived")
    meta: dict = Field(default_factory=dict, description="Additional metadata")


class DocumentListResponse(BaseModel):
    """Response for document listing endpoints."""
    documents: list[dict] = Field(default_factory=list, description="List of document summaries")


class DocumentStatusResponse(BaseModel):
    """Response for status-only operations (archive, delete, restore)."""
    status: str = Field(default="", description="Result status (e.g. 'ok', 'archived')")
    message: str = Field(default="", description="Human-readable result message")


class DocumentVersionEntry(BaseModel):
    """A single version entry in the version history."""
    num: int = Field(default=0, description="Version number")
    created_at: str = Field(default="", description="ISO timestamp")
    title: str = Field(default="", description="Document title at this version")


class DocumentVersionListResponse(BaseModel):
    """Response for the version history endpoint."""
    versions: list[dict] = Field(default_factory=list, description="Version history entries")


class DocumentTidyResponse(BaseModel):
    """Response for document tidy/cleanup operations."""
    ok: bool = Field(..., description="Whether the operation succeeded")
    count: int = Field(default=0, description="Number of documents affected")
    message: str = Field(default="", description="Human-readable result")


class DocumentPdfPreviewResponse(BaseModel):
    """Response for PDF preview generation."""
    url: str = Field(default="", description="URL to the generated preview")
    page_count: int = Field(default=0, description="Number of pages in the preview")
