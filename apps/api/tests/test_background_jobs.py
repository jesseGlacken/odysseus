"""Black-box tests for the background job system (ODY-62 / P2.7).

Tests the bg_jobs module (job launching, status tracking, completion, cleanup)
plus app startup bootstrap verification.  Covers the public API surface of
the background job infrastructure.

Scope-limited: task_scheduler decomposition + bg_monitor integration tests
deferred to ODY-62b.
"""
from __future__ import annotations

import os
import time

import pytest


# ============================================================================
# bg_jobs — Job lifecycle tests
# ============================================================================

class TestBgJobsLaunch:
    """Job launching via bg_jobs.launch()."""

    def test_launch_creates_job_record(self):
        from src.bg_jobs import launch, get
        rec = launch("echo hello", "test-session-1")
        assert rec["status"] == "running"
        assert rec["session_id"] == "test-session-1"
        assert rec["command"] == "echo hello"
        assert "id" in rec
        # Should be retrievable
        fetched = get(rec["id"])
        assert fetched is not None
        assert fetched["id"] == rec["id"]

    def test_launch_assigns_unique_ids(self):
        from src.bg_jobs import launch
        r1 = launch("echo a", "s1")
        r2 = launch("echo b", "s1")
        assert r1["id"] != r2["id"]

    def test_launch_records_timestamps(self):
        from src.bg_jobs import launch
        before = time.time()
        rec = launch("sleep 0.1", "s1")
        assert rec["started_at"] >= before
        assert rec["started_at"] <= time.time()

    def test_launch_sets_max_runtime_default(self):
        from src.bg_jobs import launch, DEFAULT_MAX_RUNTIME_S
        rec = launch("echo x", "s1")
        assert rec["max_runtime_s"] == DEFAULT_MAX_RUNTIME_S

    def test_launch_accepts_custom_max_runtime(self):
        from src.bg_jobs import launch
        rec = launch("echo x", "s1", max_runtime_s=60)
        assert rec["max_runtime_s"] == 60


class TestBgJobsRefresh:
    """Job status reconciliation via bg_jobs.refresh()."""

    def test_refresh_running_job_stays_running(self):
        from src.bg_jobs import launch, refresh
        rec = launch("sleep 300", "s1")
        jobs = refresh()
        assert jobs[rec["id"]]["status"] == "running"

    def test_refresh_detects_completed_job(self):
        from src.bg_jobs import launch, refresh, kill
        rec = launch("sleep 300", "s1")
        # Kill it so it finishes (won't write exit code, falls to 'died' path)
        kill(rec["id"])
        jobs = refresh()
        assert jobs[rec["id"]]["status"] == "failed"

    def test_refresh_idempotent(self):
        from src.bg_jobs import launch, refresh
        rec = launch("echo done", "s1")
        r1 = refresh()
        r2 = refresh()
        assert r1[rec["id"]]["status"] == r2[rec["id"]]["status"]


class TestBgJobsQuery:
    """Job queries: get(), list_for_session()."""

    def test_get_returns_none_for_missing_job(self):
        from src.bg_jobs import get
        assert get("nonexistent-id") is None

    def test_get_includes_output_field(self):
        from src.bg_jobs import launch, get
        rec = launch("echo hello world", "s1")
        fetched = get(rec["id"])
        assert fetched is not None
        assert "output" in fetched

    def test_list_for_session_filters_correctly(self):
        from src.bg_jobs import launch, list_for_session
        r1 = launch("echo a", "session-A")
        r2 = launch("echo b", "session-B")
        a_jobs = list_for_session("session-A")
        b_jobs = list_for_session("session-B")
        assert any(j["id"] == r1["id"] for j in a_jobs)
        assert any(j["id"] == r2["id"] for j in b_jobs)
        assert not any(j["id"] == r2["id"] for j in a_jobs)

    def test_list_for_session_unknown_session_empty(self):
        from src.bg_jobs import list_for_session
        assert list_for_session("nonexistent-session") == []


class TestBgJobsKill:
    """Job termination via bg_jobs.kill()."""

    def test_kill_marks_running_job_failed(self):
        from src.bg_jobs import launch, kill, get
        rec = launch("sleep 300", "s1")
        killed = kill(rec["id"])
        assert killed is not None
        assert killed["status"] == "failed"
        assert killed["killed"] is True

    def test_kill_returns_none_for_missing_job(self):
        from src.bg_jobs import kill
        assert kill("nonexistent") is None

    def test_kill_sets_followed_up(self):
        from src.bg_jobs import launch, kill
        rec = launch("sleep 300", "s1")
        killed = kill(rec["id"])
        assert killed["followed_up"] is True


class TestBgJobsFollowups:
    """Follow-up tracking: pending_followups(), mark_followed_up()."""

    def test_pending_followups_returns_unfollowed_finished_jobs(self):
        from src.bg_jobs import launch, kill, pending_followups
        rec = launch("sleep 300", "s1")
        kill(rec["id"])  # kill sets followed_up=True — so this won't appear
        # Launch another and let it finish naturally (or kill without followed_up)
        r2 = launch("echo done", "s1")
        # Manually mark it done via the store to test pending_followups
        from src.bg_jobs import _load, _save
        jobs = _load()
        if r2["id"] in jobs:
            jobs[r2["id"]]["status"] = "done"
            jobs[r2["id"]]["exit_code"] = 0
            jobs[r2["id"]]["ended_at"] = time.time()
            _save(jobs)
        pending = pending_followups()
        assert any(p["id"] == r2["id"] for p in pending)

    def test_mark_followed_up_removes_from_pending(self):
        from src.bg_jobs import launch, mark_followed_up, pending_followups
        r = launch("echo done", "s1")
        from src.bg_jobs import _load, _save
        jobs = _load()
        if r["id"] in jobs:
            jobs[r["id"]]["status"] = "done"
            jobs[r["id"]]["exit_code"] = 0
            jobs[r["id"]]["ended_at"] = time.time()
            _save(jobs)
        assert any(p["id"] == r["id"] for p in pending_followups())
        mark_followed_up(r["id"])
        assert not any(p["id"] == r["id"] for p in pending_followups())


class TestBgJobsResultText:
    """Human-readable result formatting via bg_jobs.result_text()."""

    def test_result_text_includes_command(self):
        from src.bg_jobs import result_text
        rec = {"command": "echo hello", "exit_code": 0, "log_path": "/dev/null"}
        text = result_text(rec)
        assert "echo hello" in text

    def test_result_text_killed(self):
        from src.bg_jobs import result_text
        rec = {"command": "x", "killed": True, "log_path": "/dev/null"}
        assert "killed" in result_text(rec).lower()

    def test_result_text_timed_out(self):
        from src.bg_jobs import result_text
        rec = {"command": "x", "timed_out": True, "max_runtime_s": 10, "log_path": "/dev/null"}
        assert "timed out" in result_text(rec).lower()

    def test_result_text_exit_code(self):
        from src.bg_jobs import result_text
        rec = {"command": "x", "exit_code": 42, "log_path": "/dev/null"}
        assert "42" in result_text(rec)


# ============================================================================
# App startup bootstrap
# ============================================================================

class TestAppStartup:
    """Verify the app boots without fatal errors (lifespan startup tasks)."""

    def test_app_boots_and_responds(self):
        """The app must start and serve a public endpoint."""
        from fastapi.testclient import TestClient
        from app import app
        with TestClient(app) as client:
            resp = client.get("/api/auth/status")
            assert resp.status_code == 200

    def test_app_boots_twice_idempotently(self):
        """Boot/shutdown cycles must clean up so the next boot succeeds."""
        from fastapi.testclient import TestClient
        from app import app
        with TestClient(app) as c:
            assert c.get("/api/auth/status").status_code == 200
        with TestClient(app) as c:
            assert c.get("/api/auth/status").status_code == 200

    def test_app_health_check(self):
        """A public endpoint must return valid JSON."""
        from fastapi.testclient import TestClient
        from app import app
        with TestClient(app) as client:
            resp = client.get("/api/auth/status")
            data = resp.json()
            assert isinstance(data, dict)
