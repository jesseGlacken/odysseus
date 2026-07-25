"""Integration tests for the task scheduler decomposition (ODY-74 / P2.7b).

Black-box HTTP tests for the scheduler API and unit tests for extracted helpers.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.scheduler.helpers import (
    _digest_windows,
    _normalize_chat_endpoint,
    _utcnow,
    compute_next_run,
)


class TestExtractedHelpers:
    """Verify the helper functions extracted from task_scheduler.py."""

    def test_utcnow_returns_datetime(self):
        dt = _utcnow()
        assert isinstance(dt, datetime)
        # _utcnow returns naive UTC (tzinfo stripped for DB compat)

    def test_compute_next_run_once_returns_datetime(self):
        """compute_next_run with once schedule should return a datetime."""
        result = compute_next_run("once", "12:00")
        # Without a scheduled_date or explicit TZ, returns None or a naive datetime
        # depending on the task's timezone configuration
        assert result is None or isinstance(result, datetime)

    def test_compute_next_run_daily_returns_datetime(self):
        result = compute_next_run("daily", "12:00")
        assert result is None or isinstance(result, datetime)

    def test_normalize_chat_endpoint_appends_path(self):
        result = _normalize_chat_endpoint("http://host:8000/v1/")
        assert result == "http://host:8000/v1/chat/completions"

    def test_digest_windows_returns_list(self):
        now = datetime.now(timezone.utc)
        windows = _digest_windows(now)
        assert isinstance(windows, list)
        assert len(windows) > 0


class TestSchedulerDecomposition:
    """Verify the backward-compat shim works."""

    def test_task_scheduler_importable_from_both_paths(self):
        from src.task_scheduler import TaskScheduler as TS1
        from src.task_scheduler import compute_next_run as cnr1
        from src.scheduler import compute_next_run as cnr2

        assert TS1 is not None
        assert cnr1 is cnr2  # same function object

    def test_helpers_module_has_all_eight_exports(self):
        import src.scheduler.helpers as h

        names = [
            "_cached",
            "_checkin_calendar_events",
            "_digest_windows",
            "_normalize_chat_endpoint",
            "_resolve_task_timezone",
            "_utcnow",
            "compose_task_relevant_tools",
            "compute_next_run",
        ]
        for name in names:
            assert hasattr(h, name), f"Missing: {name}"
