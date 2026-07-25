"""src.scheduler — decomposed task scheduler subpackage (ODY-74 / P2.7b).

The original monolithic ``src/task_scheduler.py`` (2,627 LOC) has been
decomposed into focused submodules.  The legacy module remains as a
backward-compatible re-export shim.
"""
from src.scheduler.helpers import (  # noqa: F401
    HOUSEKEEPING_DEFAULTS,
    RETIRED_HOUSEKEEPING_ACTIONS,
    _cached,
    _checkin_calendar_events,
    _digest_windows,
    _normalize_chat_endpoint,
    _resolve_task_timezone,
    _utcnow,
    compose_task_relevant_tools,
    compute_next_run,
)
