"""Pydantic v2 request and response models for the chat router.

These models are the source of truth for /api/chat request/response shapes.
Streaming (SSE) endpoints return StreamingResponse and cannot carry a typed
response_model; they are documented via openapi_extra in P1.3f.
"""

from pydantic import BaseModel, Field


# ── Non-streaming endpoint models ───────────────────────────────────────────

class ChatResponse(BaseModel):
    """Response from the non-streaming /api/chat endpoint."""
    response: str = Field(..., description="The model's reply text")


class ChatStopResponse(BaseModel):
    """Response from /api/chat/stop/{session_id}."""
    stopped: bool = Field(..., description="Whether the run was stopped")


class ChatStreamStatusResponse(BaseModel):
    """Response from /api/chat/stream_status/{session_id}."""
    status: str = Field(..., description="Current stream status (e.g. 'streaming')")
    detached: bool | None = Field(default=None, description="True if the run is detached from SSE")


class InjectContextResponse(BaseModel):
    """Response from /api/inject_context/{session_id}."""
    status: str = Field(..., description="Result status message")


class ChatSearchResult(BaseModel):
    """A single chat message search result."""
    session_id: str = Field(default="", description="Session ID containing the message")
    message_id: str = Field(default="", description="Message ID")
    role: str = Field(default="", description="Message role (user/assistant)")
    content: str = Field(default="", description="Message content snippet")
    timestamp: str = Field(default="", description="ISO-format timestamp")
    session_name: str | None = Field(default=None, description="Session display name")


# Re-use from chat_routes for the non-streaming endpoint response
# Note: dict[str, Any] is used for search results because the schema is
# dynamic per-result; see ADR-0008 §5 for input validation layering.
