"""src.calendar_helpers — calendar date/time utilities (ODY-22 / P2.4).

Extracted from routes/calendar_routes.py so domain code and background
workers can use these helpers without importing from routes/ (which violates
ADR-0001 layering).

routes/calendar_routes.py re-exports these names for backward compatibility.

Public API
----------
_ensure_positive_duration(start_dt, end_dt, all_day) -> datetime
    Clamp event end to be strictly after start.

_parse_dt(s) -> datetime
    Parse a date/datetime string to a naive-local datetime.

parse_due_for_user(s) -> str
    Parse a date/datetime string in the user's timezone, returning an ISO 8601
    string with explicit offset where available.
"""
from __future__ import annotations

import re as _re
from datetime import datetime, timedelta
from typing import Optional


# ---------------------------------------------------------------------------
# _ensure_positive_duration
# ---------------------------------------------------------------------------

def _ensure_positive_duration(
    start_dt: datetime,
    end_dt: Optional[datetime],
    all_day: bool,
) -> datetime:
    """Clamp an imported event's end so it has a positive duration.

    Some .ics exporters write a single-day all-day event with DTEND equal to
    DTSTART (treating DTEND as inclusive rather than the RFC 5545 exclusive
    bound). Stored verbatim that produces a zero-duration row, which the
    list_events overlap filter (dtstart < end AND dtend > start) silently
    drops — the event never appears on the calendar even though the web UI
    would otherwise show it. Normalize a non-positive end to the same default
    span used when DTEND is absent: one day for all-day events, one hour
    otherwise.
    """
    if end_dt <= start_dt:
        return start_dt + (timedelta(days=1) if all_day else timedelta(hours=1))
    return end_dt


# ---------------------------------------------------------------------------
# _parse_dt  (naive-local; matches DB schema for CalendarEvent.dtstart)
# ---------------------------------------------------------------------------

def _parse_dt(s: str) -> datetime:
    """Parse a date/datetime string to a naive-local datetime.

    Strict ISO first (cheapest path; this is what most callers pass). On
    failure, fall through a small natural-language parser that handles the
    phrasings LLMs commonly emit when given prompts like "1pm tomorrow":
      - today/tonight/tomorrow/yesterday [at] HH(:MM)? (am/pm)?
      - next <weekday> [at] HH(:MM)? (am/pm)?
      - in N hour(s)/minute(s)/day(s)
      - bare time today: "1pm", "13:00"
      - YYYY-MM-DD optionally followed by time
    Anything still unparsed falls to dateutil.parser, which handles most
    other absolute formats. Local-naive datetimes returned to match the
    DB schema (CalendarEvent.dtstart is naive).
    """
    s = (s or "").strip()
    if not s:
        raise ValueError("empty datetime string")

    # Fast path: strict ISO
    try:
        if len(s) == 10:
            return datetime.fromisoformat(s)
        _s2 = s.replace("Z", "+00:00") if s.endswith("Z") else s
        parsed = datetime.fromisoformat(_s2)
        # Strip tz for legacy callers — they expect naive.
        if parsed.tzinfo is not None:
            from datetime import timezone as _tz
            return parsed.astimezone(_tz.utc).replace(tzinfo=None)
        return parsed
    except ValueError:
        pass

    now = datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    lower = s.lower().strip()

    def _parse_time(t: str):
        """Return (hour, minute) from '1pm', '1:30 PM', '13:00', etc., or None."""
        t = _re.sub(r'\b([ap])\s*\.?\s*m\.?\b', r'\1m', t.strip(), flags=_re.IGNORECASE)
        m = _re.match(r'^\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s*$', t, _re.IGNORECASE)
        if not m:
            return None
        h = int(m.group(1))
        mn = int(m.group(2) or 0)
        ampm = (m.group(3) or "").lower()
        if ampm == "pm" and h < 12:
            h += 12
        elif ampm == "am" and h == 12:
            h = 0
        if not (0 <= h < 24 and 0 <= mn < 60):
            return None
        return h, mn

    # today/tonight/tomorrow/yesterday [at] TIME
    m = _re.match(r'^(today|tonight|tomorrow|tmrw|yesterday)(?:\s+at)?\s*(.*)$', lower)
    if m:
        word, rest = m.group(1), m.group(2).strip()
        base = today
        if word in ("tomorrow", "tmrw"):
            base = today + timedelta(days=1)
        elif word == "yesterday":
            base = today - timedelta(days=1)
        if not rest:
            return base
        t = _parse_time(rest)
        if t is not None:
            return base.replace(hour=t[0], minute=t[1])

    # time-first: "3pm today", "9am tomorrow", "11pm tonight"
    m = _re.match(r'^(.+?)\s+(today|tonight|tomorrow|tmrw|yesterday)$', lower)
    if m:
        time_part, word = m.group(1).strip(), m.group(2)
        base = today
        if word in ("tomorrow", "tmrw"):
            base = today + timedelta(days=1)
        elif word == "yesterday":
            base = today - timedelta(days=1)
        t = _parse_time(time_part)
        if t is not None:
            return base.replace(hour=t[0], minute=t[1])

    # next <weekday> [at] TIME
    weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    m = _re.match(r'^next\s+(\w+)(?:\s+at)?\s*(.*)$', lower)
    if m and m.group(1) in weekdays:
        target_dow = weekdays.index(m.group(1))
        days = (target_dow - today.weekday()) % 7 or 7
        base = today + timedelta(days=days)
        rest = m.group(2).strip()
        if not rest:
            return base
        t = _parse_time(rest)
        if t is not None:
            return base.replace(hour=t[0], minute=t[1])

    # in N hours/minutes/days
    m = _re.match(r'^in\s+(\d+)\s*(hour|hr|minute|min|day)s?\s*$', lower)
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        if unit in ("hour", "hr"):
            return now + timedelta(hours=n)
        if unit in ("minute", "min"):
            return now + timedelta(minutes=n)
        if unit == "day":
            return now + timedelta(days=n)

    # Bare time → today at that time
    t = _parse_time(lower)
    if t is not None:
        return today.replace(hour=t[0], minute=t[1])

    # Last resort: dateutil's fuzzy parser
    try:
        from dateutil import parser as _du
        parsed = _du.parse(s)
        if parsed.tzinfo is not None:
            from datetime import timezone as _tz
            return parsed.astimezone(_tz.utc).replace(tzinfo=None)
        return parsed
    except Exception:
        raise ValueError(f"could not parse datetime: {s!r}")


# ---------------------------------------------------------------------------
# parse_due_for_user  (tz-aware; used by note and calendar tools)
# ---------------------------------------------------------------------------

def parse_due_for_user(s: str) -> str:
    """Parse a due-date string emitted by the LLM / agent in the USER's tz.

    Returns an ISO 8601 string with explicit offset (e.g.
    ``"2026-05-13T21:00:00+09:00"``) so downstream consumers preserve the
    absolute moment. Falls back to the legacy naive ISO when no user offset
    is set.

    Handles three input shapes:

    * Tz-aware ISO (``"...Z"`` or ``"...+09:00"``) → returned as ISO with offset.
    * Naive ISO (``"2026-05-13T21:00:00"``) → attach the user's offset.
    * Natural-language (``"today at 9pm"``, ``"tomorrow 14:00"``,
      ``"in 2 hours"``) → evaluated against the user's local "now" instead of
      the server's, then ISO-with-offset.
    """
    from datetime import timedelta as _td
    from src.user_time import (
        get_user_tz_name,
        get_user_tz_offset,
        now_user_local,
        user_timezone,
    )

    offset = get_user_tz_offset()
    tz_name = get_user_tz_name()
    s = (s or "").strip()
    if not s:
        return s

    # Tz-aware ISO short-circuit — preserve as-is.
    try:
        _s2 = s.replace("Z", "+00:00") if s.endswith("Z") else s
        parsed = datetime.fromisoformat(_s2)
        if parsed.tzinfo is not None:
            return parsed.isoformat()
    except ValueError:
        parsed = None

    if offset is None and not tz_name:
        # No user tz known — preserve legacy behavior (naive server-local).
        return _parse_dt(s).isoformat()

    user_tz = user_timezone()

    # Naive ISO → tag with user tz.
    if parsed is not None and parsed.tzinfo is None:
        return parsed.replace(tzinfo=user_tz).isoformat()

    # Natural language — evaluate against user's "now".
    from datetime import timezone as _tz2
    server_now_utc = datetime.now(_tz2.utc)
    user_now = now_user_local(server_now_utc)
    lower = s.lower().strip()

    def _parse_time(t: str):
        t = _re.sub(r'\b([ap])\s*\.?\s*m\.?\b', r'\1m', t.strip(), flags=_re.IGNORECASE)
        m = _re.match(r'^\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s*$', t, _re.IGNORECASE)
        if not m:
            return None
        h = int(m.group(1))
        mn = int(m.group(2) or 0)
        ampm = (m.group(3) or "").lower()
        if ampm == "pm" and h < 12:
            h += 12
        elif ampm == "am" and h == 12:
            h = 0
        if not (0 <= h < 24 and 0 <= mn < 60):
            return None
        return h, mn

    today = user_now.replace(hour=0, minute=0, second=0, microsecond=0)

    m = _re.match(r'^(today|tonight|tomorrow|tmrw|yesterday)(?:\s+at)?\s*(.*)$', lower)
    if m:
        word, rest = m.group(1), m.group(2).strip()
        base = today
        if word in ("tomorrow", "tmrw"):
            base = today + _td(days=1)
        elif word == "yesterday":
            base = today - _td(days=1)
        if not rest:
            return base.isoformat()
        t = _parse_time(rest)
        if t is not None:
            return base.replace(hour=t[0], minute=t[1]).isoformat()

    # Time-first: "3pm today", "11pm today", "9am tomorrow"
    m = _re.match(r'^(.+?)\s+(today|tonight|tomorrow|tmrw|yesterday)$', lower)
    if m:
        time_part, word = m.group(1).strip(), m.group(2)
        base = today
        if word in ("tomorrow", "tmrw"):
            base = today + _td(days=1)
        elif word == "yesterday":
            base = today - _td(days=1)
        t = _parse_time(time_part)
        if t is not None:
            return base.replace(hour=t[0], minute=t[1]).isoformat()

    m = _re.match(r'^in\s+(\d+)\s*(hour|hr|minute|min|day)s?\s*$', lower)
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        if unit in ("hour", "hr"):
            return (user_now + _td(hours=n)).isoformat()
        if unit in ("minute", "min"):
            return (user_now + _td(minutes=n)).isoformat()
        if unit == "day":
            return (user_now + _td(days=n)).isoformat()

    t = _parse_time(lower)
    if t is not None:
        return today.replace(hour=t[0], minute=t[1]).isoformat()

    # Last resort: dateutil. Trust it but apply user tz if it returned naive.
    try:
        from dateutil import parser as _du
        parsed2 = _du.parse(s)
        if parsed2.tzinfo is None:
            parsed2 = parsed2.replace(tzinfo=user_tz)
        return parsed2.isoformat()
    except Exception:
        # Final fallback: legacy parser, naive.
        return _parse_dt(s).isoformat()
