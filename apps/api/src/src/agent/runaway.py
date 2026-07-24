"""
agent/runaway.py — Runaway-loop detection for the streaming agent loop.

Identifies identical repeated tool calls (same tool AND arguments) and
surfaces the offending tool name when a hard threshold is crossed.  Counting
by identical signature — not per tool-type totals — means a legitimate batch
of distinct calls to one tool (e.g. 18 ``manage_calendar create_event`` calls)
is never flagged.
"""
from __future__ import annotations

import collections


def _detect_runaway_call(
    call_freq: collections.Counter,
    threshold: int = 15,
) -> str | None:
    """Return the tool name of a call signature repeated >= *threshold* times.

    ``call_freq`` is a :class:`collections.Counter` keyed by
    ``"{tool_type}:{content[:120]}"``.  Returns ``None`` when no signature
    crosses the threshold.
    """
    sig = next((s for s, n in call_freq.items() if n >= threshold), None)
    return sig.split(":", 1)[0] if sig else None
