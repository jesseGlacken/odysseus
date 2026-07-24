"""Black-box tests for src.calendar_helpers (ODY-22 / P2.4).

Covers _ensure_positive_duration, _parse_dt, and parse_due_for_user.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest


# ---------------------------------------------------------------------------
# _ensure_positive_duration
# ---------------------------------------------------------------------------

class TestEnsurePositiveDuration:
    def test_positive_duration_unchanged(self):
        from src.calendar_helpers import _ensure_positive_duration
        start = datetime(2026, 5, 1, 10, 0)
        end = datetime(2026, 5, 1, 11, 0)
        assert _ensure_positive_duration(start, end, all_day=False) == end

    def test_zero_duration_allday_clamps_to_one_day(self):
        from src.calendar_helpers import _ensure_positive_duration
        dt = datetime(2026, 5, 1)
        result = _ensure_positive_duration(dt, dt, all_day=True)
        assert result == dt + timedelta(days=1)

    def test_zero_duration_timed_clamps_to_one_hour(self):
        from src.calendar_helpers import _ensure_positive_duration
        dt = datetime(2026, 5, 1, 14, 0)
        result = _ensure_positive_duration(dt, dt, all_day=False)
        assert result == dt + timedelta(hours=1)

    def test_end_before_start_allday(self):
        from src.calendar_helpers import _ensure_positive_duration
        start = datetime(2026, 5, 2)
        end = datetime(2026, 5, 1)
        result = _ensure_positive_duration(start, end, all_day=True)
        assert result == start + timedelta(days=1)

    def test_end_before_start_timed(self):
        from src.calendar_helpers import _ensure_positive_duration
        start = datetime(2026, 5, 1, 15, 0)
        end = datetime(2026, 5, 1, 14, 0)
        result = _ensure_positive_duration(start, end, all_day=False)
        assert result == start + timedelta(hours=1)


# ---------------------------------------------------------------------------
# _parse_dt
# ---------------------------------------------------------------------------

class TestParseDt:
    def test_iso_date_only(self):
        from src.calendar_helpers import _parse_dt
        result = _parse_dt("2026-05-13")
        assert result == datetime(2026, 5, 13)

    def test_iso_datetime(self):
        from src.calendar_helpers import _parse_dt
        result = _parse_dt("2026-05-13T14:30:00")
        assert result == datetime(2026, 5, 13, 14, 30, 0)

    def test_iso_utc_strips_tz(self):
        from src.calendar_helpers import _parse_dt
        result = _parse_dt("2026-05-13T14:30:00Z")
        # Result is naive UTC
        assert result.tzinfo is None
        assert result == datetime(2026, 5, 13, 14, 30, 0)

    def test_natural_tomorrow(self):
        from src.calendar_helpers import _parse_dt
        result = _parse_dt("tomorrow")
        tomorrow = (datetime.now() + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        assert result == tomorrow

    def test_natural_today_at_3pm(self):
        from src.calendar_helpers import _parse_dt
        result = _parse_dt("today at 3pm")
        today = datetime.now().replace(hour=15, minute=0, second=0, microsecond=0)
        assert result == today

    def test_natural_in_2_hours(self):
        from src.calendar_helpers import _parse_dt
        import time
        before = datetime.now()
        result = _parse_dt("in 2 hours")
        after = datetime.now()
        assert before + timedelta(hours=2) <= result <= after + timedelta(hours=2)

    def test_empty_string_raises(self):
        from src.calendar_helpers import _parse_dt
        with pytest.raises(ValueError):
            _parse_dt("")

    def test_unrecognised_string_raises(self):
        from src.calendar_helpers import _parse_dt
        with pytest.raises((ValueError, Exception)):
            _parse_dt("not a date at all !!!")


# ---------------------------------------------------------------------------
# parse_due_for_user
# ---------------------------------------------------------------------------

class TestParseDueForUser:
    """Tests run with no user tz context set (falls back to legacy naive behavior)."""

    def test_empty_returns_empty(self):
        from src.calendar_helpers import parse_due_for_user
        assert parse_due_for_user("") == ""

    def test_aware_iso_z_returned_as_is(self):
        from src.calendar_helpers import parse_due_for_user
        result = parse_due_for_user("2026-05-13T21:00:00Z")
        # Should preserve tz info
        assert "2026-05-13" in result

    def test_aware_iso_offset_returned_as_is(self):
        from src.calendar_helpers import parse_due_for_user
        result = parse_due_for_user("2026-05-13T21:00:00+09:00")
        assert "2026-05-13" in result

    def test_naive_iso_returns_some_isoformat(self):
        from src.calendar_helpers import parse_due_for_user
        result = parse_due_for_user("2026-05-13T14:30:00")
        assert result.startswith("2026-05-13T14:30:00")

    def test_importable_from_calendar_helpers(self):
        from src.calendar_helpers import parse_due_for_user
        assert callable(parse_due_for_user)


# ---------------------------------------------------------------------------
# Validators backward compat
# ---------------------------------------------------------------------------

class TestValidatorsBackwardCompat:
    def test_routes_validators_exports_validate_remote_host(self):
        from routes._validators import validate_remote_host
        from src.validators import validate_remote_host as direct
        assert validate_remote_host is direct

    def test_routes_validators_exports_validate_ssh_port(self):
        from routes._validators import validate_ssh_port
        from src.validators import validate_ssh_port as direct
        assert validate_ssh_port is direct


# ---------------------------------------------------------------------------
# Cookbook helpers backward compat
# ---------------------------------------------------------------------------

class TestCookbookHelpersBackwardCompat:
    def test_routes_cookbook_helpers_exports_load_stored_hf_token(self):
        from routes.cookbook_helpers import load_stored_hf_token
        from src.cookbook_helpers import load_stored_hf_token as direct
        assert load_stored_hf_token is direct
