"""Pydantic v2 response models for the email router (P1.3d).

Email is the largest route module (5,226 LOC). These models cover the common
return shapes. Endpoints returning StreamingResponse or raw bytes are excluded.
"""

from pydantic import BaseModel, Field


class EmailStatusResponse(BaseModel):
    """Generic status response for email operations (flag, mark, move, delete)."""
    ok: bool = Field(..., description="Whether the operation succeeded")
    message: str = Field(default="", description="Human-readable result")


class EmailContactResponse(BaseModel):
    """Response for email contact resolution."""
    name: str = Field(default="", description="Contact display name")
    email: str = Field(default="", description="Contact email address")


class EmailContactListResponse(BaseModel):
    """Response for contacts list endpoint."""
    contacts: list[dict] = Field(default_factory=list, description="Contact entries")


class EmailUnreadStateResponse(BaseModel):
    """Response for unread state endpoint."""
    unread: int = Field(default=0, description="Count of unread messages")


class EmailFoldersResponse(BaseModel):
    """Response for folder/mailbox listing."""
    folders: list[str] = Field(default_factory=list, description="IMAP folder names")


class EmailScheduledCountResponse(BaseModel):
    """Response for scheduled/pending email counts."""
    count: int = Field(default=0, description="Number of items")


class EmailComposeUploadResponse(BaseModel):
    """Response for compose attachment upload."""
    token: str = Field(default="", description="Upload token for the attachment")


class EmailExtractStyleResponse(BaseModel):
    """Response for signature/style extraction."""
    style: dict = Field(default_factory=dict, description="Extracted style properties")


class EmailSummarizeResponse(BaseModel):
    """Response for email summarization."""
    summary: str = Field(default="", description="Summarized email content")


class EmailTranslateResponse(BaseModel):
    """Response for email translation."""
    translation: str = Field(default="", description="Translated email content")
