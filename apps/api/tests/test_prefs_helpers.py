"""Black-box tests for src.prefs_helpers (ODY-22 / P2.4).

Tests exercise the public interface of the prefs helpers through the module's
public API — no mocking of internal file-I/O; we use a real temp directory.
"""
from __future__ import annotations

import json
import os
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture()
def prefs_file(tmp_path, monkeypatch):
    """Point _PREFS_FILE at a fresh temp file for each test."""
    path = tmp_path / "user_prefs.json"
    import src.prefs_helpers as ph
    monkeypatch.setattr(ph, "_PREFS_FILE", str(path))
    return path


# ---------------------------------------------------------------------------
# _load / _save  (flat round-trip)
# ---------------------------------------------------------------------------

class TestLoadSaveFlat:
    def test_load_missing_returns_empty_dict(self, prefs_file):
        from src.prefs_helpers import _load
        assert _load() == {}

    def test_save_and_load_round_trip(self, prefs_file):
        from src.prefs_helpers import _load, _save
        _save({"theme": "dark", "lang": "en"})
        assert _load() == {"theme": "dark", "lang": "en"}

    def test_save_is_atomic(self, prefs_file):
        """File should never be half-written (tmp+rename pattern)."""
        from src.prefs_helpers import _load, _save
        _save({"v": 1})
        _save({"v": 2})
        assert _load() == {"v": 2}

    def test_load_corrupted_returns_empty(self, prefs_file):
        prefs_file.write_text("not valid json", encoding="utf-8")
        from src.prefs_helpers import _load
        assert _load() == {}

    def test_load_array_returns_empty(self, prefs_file):
        """Only dict-shaped files are valid; arrays return {}."""
        prefs_file.write_text("[1, 2, 3]", encoding="utf-8")
        from src.prefs_helpers import _load
        assert _load() == {}


# ---------------------------------------------------------------------------
# _load_for_user / _save_for_user  (multi-user format)
# ---------------------------------------------------------------------------

class TestLoadForUserLegacyFlat:
    """When the file has no _users key (legacy single-user format)."""

    def test_returns_flat_prefs_when_no_users_key(self, prefs_file):
        from src.prefs_helpers import _load_for_user, _save
        _save({"theme": "light"})
        assert _load_for_user("alice") == {"theme": "light"}

    def test_none_user_also_returns_flat_prefs(self, prefs_file):
        from src.prefs_helpers import _load_for_user, _save
        _save({"x": 1})
        assert _load_for_user(None) == {"x": 1}

    def test_missing_file_returns_empty(self, prefs_file):
        from src.prefs_helpers import _load_for_user
        assert _load_for_user("alice") == {}


class TestLoadForUserMulti:
    """When the file has _users dict (multi-user format)."""

    def _write_multiuser(self, prefs_file, users: dict):
        prefs_file.write_text(json.dumps({"_users": users}), encoding="utf-8")

    def test_returns_correct_user_prefs(self, prefs_file):
        self._write_multiuser(prefs_file, {"alice": {"theme": "dark"}, "bob": {"theme": "light"}})
        from src.prefs_helpers import _load_for_user
        assert _load_for_user("alice") == {"theme": "dark"}
        assert _load_for_user("bob") == {"theme": "light"}

    def test_unknown_user_returns_empty(self, prefs_file):
        self._write_multiuser(prefs_file, {"alice": {"x": 1}})
        from src.prefs_helpers import _load_for_user
        assert _load_for_user("carol") == {}

    def test_none_user_returns_first_users_prefs(self, prefs_file):
        """None user (auth off) reads from first slot for backward compat."""
        self._write_multiuser(prefs_file, {"alice": {"theme": "dark"}})
        from src.prefs_helpers import _load_for_user
        assert _load_for_user(None) == {"theme": "dark"}

    def test_returns_copy_not_reference(self, prefs_file):
        self._write_multiuser(prefs_file, {"alice": {"x": 1}})
        from src.prefs_helpers import _load_for_user
        prefs1 = _load_for_user("alice")
        prefs1["x"] = 99
        prefs2 = _load_for_user("alice")
        assert prefs2["x"] == 1  # mutation didn't persist


class TestSaveForUser:
    def test_creates_multiuser_file_for_named_user(self, prefs_file):
        from src.prefs_helpers import _save_for_user, _load_for_user
        _save_for_user("alice", {"theme": "dark"})
        assert _load_for_user("alice") == {"theme": "dark"}

    def test_preserves_other_users_when_saving(self, prefs_file):
        from src.prefs_helpers import _save_for_user, _load_for_user
        _save_for_user("alice", {"x": 1})
        _save_for_user("bob", {"y": 2})
        assert _load_for_user("alice") == {"x": 1}
        assert _load_for_user("bob") == {"y": 2}

    def test_none_user_writes_flat_when_no_existing_users(self, prefs_file):
        from src.prefs_helpers import _save_for_user, _load
        _save_for_user(None, {"theme": "red"})
        data = _load()
        # Flat format: no _users wrapper
        assert "_users" not in data
        assert data["theme"] == "red"

    def test_none_user_writes_into_first_slot_when_multiuser_exists(self, prefs_file):
        from src.prefs_helpers import _save_for_user, _load_for_user
        _save_for_user("alice", {"theme": "blue"})
        _save_for_user("bob", {"theme": "green"})
        # Now write with user=None — should update the first slot (alice)
        _save_for_user(None, {"theme": "purple"})
        # bob should still have his prefs
        assert _load_for_user("bob") == {"theme": "green"}

    def test_overwrite_same_user(self, prefs_file):
        from src.prefs_helpers import _save_for_user, _load_for_user
        _save_for_user("alice", {"x": 1})
        _save_for_user("alice", {"x": 99, "y": 2})
        assert _load_for_user("alice") == {"x": 99, "y": 2}


# ---------------------------------------------------------------------------
# Import-path backward compatibility
# ---------------------------------------------------------------------------

class TestBackwardCompatImports:
    def test_prefs_routes_still_exports_load_for_user(self):
        """routes.prefs_routes re-exports _load_for_user from src.prefs_helpers."""
        from routes.prefs_routes import _load_for_user
        from src.prefs_helpers import _load_for_user as direct
        assert _load_for_user is direct

    def test_prefs_routes_still_exports_save_for_user(self):
        from routes.prefs_routes import _save_for_user
        from src.prefs_helpers import _save_for_user as direct
        assert _save_for_user is direct

    def test_prefs_routes_still_exports_load(self):
        from routes.prefs_routes import _load
        from src.prefs_helpers import _load as direct
        assert _load is direct
