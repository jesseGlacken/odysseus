"""Black-box tests for UserRepository (ODY-20 / P2.3).

Tests exercise the repository's public interface only — no access to
AuthManager internals or private dict keys.  Each test gets a fresh
AuthManager pointed at a temporary directory so tests are fully isolated.

Following ADR-0004: black-box, no mocks of internal collaborators.
The only external boundary controlled here is the filesystem (temporary
directory injected via pytest fixtures).
"""
from __future__ import annotations

import os
import tempfile
from typing import Generator

import pytest

from core.auth import AuthManager
from src.infra.repositories.user_repository import UserRecord, UserRepository


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def auth_manager() -> Generator[AuthManager, None, None]:
    """Provide an AuthManager pointed at a fresh temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        auth_path = os.path.join(tmpdir, "auth.json")
        yield AuthManager(auth_path=auth_path)


@pytest.fixture()
def repo(auth_manager: AuthManager) -> UserRepository:
    """Provide a UserRepository wrapping the fixture AuthManager."""
    return UserRepository(auth_manager)


@pytest.fixture()
def seeded_repo(repo: UserRepository) -> UserRepository:
    """Repository with one admin user ('alice') already created."""
    result = repo.create_user("alice", "s3cr3t!", is_admin=True)
    assert result is not None, "Fixture pre-condition: alice must be created"
    return repo


# ---------------------------------------------------------------------------
# create_user
# ---------------------------------------------------------------------------

class TestCreateUser:
    def test_creates_user_and_returns_record(self, repo: UserRepository) -> None:
        record = repo.create_user("bob", "password123")
        assert record is not None
        assert record.username == "bob"
        assert record.is_admin is False

    def test_admin_flag_is_stored(self, repo: UserRepository) -> None:
        record = repo.create_user("alice", "password123", is_admin=True)
        assert record is not None
        assert record.is_admin is True

    def test_duplicate_username_returns_none(self, repo: UserRepository) -> None:
        repo.create_user("bob", "first")
        second = repo.create_user("bob", "second")
        assert second is None

    def test_normalises_username_to_lowercase(self, repo: UserRepository) -> None:
        record = repo.create_user("Alice", "password123")
        assert record is not None
        assert record.username == "alice"

    def test_password_hash_is_not_plaintext(self, repo: UserRepository) -> None:
        record = repo.create_user("carol", "myplaintext")
        assert record is not None
        # bcrypt hashes start with $2b$ (or $2a$)
        assert record.password_hash.startswith("$2")
        assert "myplaintext" not in record.password_hash


# ---------------------------------------------------------------------------
# get / get_by_username
# ---------------------------------------------------------------------------

class TestGet:
    def test_get_existing_user(self, seeded_repo: UserRepository) -> None:
        record = seeded_repo.get("alice")
        assert record is not None
        assert record.username == "alice"

    def test_get_missing_user_returns_none(self, repo: UserRepository) -> None:
        assert repo.get("nobody") is None

    def test_get_by_username_is_case_insensitive(self, seeded_repo: UserRepository) -> None:
        record = seeded_repo.get_by_username("ALICE")
        assert record is not None
        assert record.username == "alice"

    def test_get_by_username_missing_returns_none(self, repo: UserRepository) -> None:
        assert repo.get_by_username("ghost") is None


# ---------------------------------------------------------------------------
# exists
# ---------------------------------------------------------------------------

class TestExists:
    def test_true_for_created_user(self, seeded_repo: UserRepository) -> None:
        assert seeded_repo.exists("alice") is True

    def test_false_for_missing_user(self, repo: UserRepository) -> None:
        assert repo.exists("nobody") is False

    def test_case_insensitive(self, seeded_repo: UserRepository) -> None:
        assert seeded_repo.exists("ALICE") is True


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------

class TestList:
    def test_empty_store_returns_empty_list(self, repo: UserRepository) -> None:
        assert repo.list() == []

    def test_returns_all_users(self, repo: UserRepository) -> None:
        repo.create_user("alice", "pw", is_admin=True)
        repo.create_user("bob", "pw")
        users = repo.list()
        usernames = {u.username for u in users}
        assert usernames == {"alice", "bob"}

    def test_returns_userrecord_instances(self, seeded_repo: UserRepository) -> None:
        for record in seeded_repo.list():
            assert isinstance(record, UserRecord)

    def test_unknown_filter_raises_typeerror(self, repo: UserRepository) -> None:
        with pytest.raises(TypeError, match="does not support filter"):
            repo.list(email="x@example.com")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# save (upsert)
# ---------------------------------------------------------------------------

class TestSave:
    def test_create_via_save_with_hashed_password(self, repo: UserRepository) -> None:
        # Build a UserRecord with a known bcrypt hash and persist it.
        import bcrypt
        pw_hash = bcrypt.hashpw(b"testpw", bcrypt.gensalt()).decode()
        record = UserRecord(
            username="dave",
            is_admin=False,
            created=1_700_000_000.0,
            privileges={},
            password_hash=pw_hash,
        )
        saved = repo.save(record)
        assert saved.username == "dave"
        assert saved.is_admin is False

    def test_save_updates_existing_user(self, seeded_repo: UserRepository) -> None:
        original = seeded_repo.get("alice")
        assert original is not None
        updated = UserRecord(
            username=original.username,
            is_admin=False,  # demote
            created=original.created,
            privileges=original.privileges,
            password_hash=original.password_hash,
        )
        saved = seeded_repo.save(updated)
        assert saved.is_admin is False
        # Reload from repo to confirm persistence
        reloaded = seeded_repo.get("alice")
        assert reloaded is not None
        assert reloaded.is_admin is False

    def test_save_empty_username_raises_valueerror(self, repo: UserRepository) -> None:
        record = UserRecord(
            username="",
            is_admin=False,
            created=0.0,
            privileges={},
            password_hash="",
        )
        with pytest.raises(ValueError, match="username must not be empty"):
            repo.save(record)


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------

class TestDelete:
    def test_delete_existing_user_returns_true(self, seeded_repo: UserRepository) -> None:
        assert seeded_repo.delete("alice") is True
        assert seeded_repo.exists("alice") is False

    def test_delete_missing_user_returns_false(self, repo: UserRepository) -> None:
        assert repo.delete("nobody") is False

    def test_delete_is_idempotent(self, seeded_repo: UserRepository) -> None:
        seeded_repo.delete("alice")
        # Second delete must not raise
        assert seeded_repo.delete("alice") is False

    def test_deleted_user_not_in_list(self, seeded_repo: UserRepository) -> None:
        seeded_repo.delete("alice")
        assert all(u.username != "alice" for u in seeded_repo.list())


# ---------------------------------------------------------------------------
# set_admin
# ---------------------------------------------------------------------------

class TestSetAdmin:
    def test_promote_non_admin_to_admin(self, repo: UserRepository) -> None:
        # Need at least one admin to call set_admin
        repo.create_user("admin", "pw", is_admin=True)
        repo.create_user("bob", "pw", is_admin=False)
        ok = repo.set_admin("bob", True, requesting_user="admin")
        assert ok is True
        record = repo.get("bob")
        assert record is not None
        assert record.is_admin is True

    def test_set_admin_unknown_user_returns_false(self, seeded_repo: UserRepository) -> None:
        ok = seeded_repo.set_admin("nobody", True, requesting_user="alice")
        assert ok is False

    def test_set_admin_requires_admin_requester(self, repo: UserRepository) -> None:
        repo.create_user("admin", "pw", is_admin=True)
        repo.create_user("regular", "pw", is_admin=False)
        ok = repo.set_admin("admin", False, requesting_user="regular")
        assert ok is False
