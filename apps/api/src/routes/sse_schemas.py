"""OpenAPI extra schemas for SSE (Server-Sent Events) streaming endpoints.

Streaming endpoints return text/event-stream and cannot use a standard
Pydantic response_model. These openapi_extra dicts document the event
stream structure in the OpenAPI schema. Applied via the route decorator's
openapi_extra parameter.

See ADR-0012 §2 (Observability) and P1.3f.
"""

# Shared SSE response schema — used by all streaming endpoints.
# Individual endpoints may extend this with specific event types.
SSE_RESPONSE = {
    "responses": {
        "200": {
            "description": "Server-Sent Events stream",
            "content": {
                "text/event-stream": {
                    "schema": {
                        "type": "object",
                        "description": "SSE event stream. Each event has an event: type and data: payload.",
                        "properties": {
                            "event": {
                                "type": "string",
                                "description": "Event type (e.g. token, tool_start, tool_output, done, error)",
                            },
                            "data": {
                                "type": "string",
                                "description": "JSON-encoded event payload",
                            },
                        },
                    }
                }
            },
        }
    }
}

# Chat SSE event types
CHAT_SSE_EXTRA = {
    **SSE_RESPONSE,
    "description": "Streaming chat completion via SSE. Events: token (text delta), "
    "tool_start/tool_progress/tool_output (tool execution), "
    "model_info (model metadata), done (completion), error (failure).",
}

# Chat resume SSE
CHAT_RESUME_SSE_EXTRA = {
    **SSE_RESPONSE,
    "description": "Resume a detached streaming chat session. Same event types as chat_stream.",
}

# Rewrite SSE
REWRITE_SSE_EXTRA = {
    **SSE_RESPONSE,
    "description": "Rewrite the last AI message without running the agent loop. "
    "Events: token (rewritten text), done, error.",
}

# Shell/command output SSE
SHELL_SSE_EXTRA = {
    **SSE_RESPONSE,
    "description": "Stream shell command output. Events: stdout (output line), "
    "stderr (error line), exit (exit code), error (failure).",
}

# Model download/serve SSE
MODEL_SSE_EXTRA = {
    **SSE_RESPONSE,
    "description": "Stream model download or serve progress. Events: progress (status update), "
    "done (complete), error (failure).",
}

# Research SSE
RESEARCH_SSE_EXTRA = {
    **SSE_RESPONSE,
    "description": "Stream deep research progress. Events: step (research step), "
    "source (found source), done (complete), error (failure).",
}

# Email streaming SSE
EMAIL_SSE_EXTRA = {
    **SSE_RESPONSE,
    "description": "Stream email content or AI-generated reply. Events: token (text delta), "
    "done, error.",
}

# Codex/zip download SSE
CODEX_SSE_EXTRA = {
    **SSE_RESPONSE,
    "description": "Stream codex zip download progress. Events: progress, done, error.",
}
