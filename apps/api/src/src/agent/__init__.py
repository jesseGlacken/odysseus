"""src.agent — decomposed agent-loop package (ODY-18).

Public API re-exported for callers that import from ``src.agent`` directly.
The primary entry-point is ``stream_agent_loop`` in ``src.agent.loop``.
"""
from src.agent.loop import (
    PLAN_MODE_DIRECTIVE,
    build_active_plan_note,
    stream_agent_loop,
)

__all__ = [
    "stream_agent_loop",
    "build_active_plan_note",
    "PLAN_MODE_DIRECTIVE",
]
