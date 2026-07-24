"""Black-box tests for SessionRepository (ODY-20 / P2.3).

Tests exercise the repository's public interface through a real in-memory
SQLite database.  ``Base.metadata.create_all`` creates a schema identical to
production; no mocks are used for database access.

Following ADR-0004: black-box tests only.  The only external boundary
controlled here is the database (SQLite in-memory, injected via fixtures).
"""
from __future__ import annotations

import uuid
from typing import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as DbSession, sessionmaker
from sqlalchemy.pool import StaticPool

from core.database import Base, Session as ChatSession
from src.infra.repositories.session_repository import SessionRepository


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def _engine():
    """Module-scoped in-memory SQLite engine with a StaticPool.

    StaticPool ensures that all connections within the test module share the
    same in-memory database, so ``Base.metadata.create_all`` and subsequent
    queries all see the same schema and data.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def db_session(_engine) -> Generator[DbSession, None, None]:
    """Function-scoped database session, rolled back after each test."""
    _Session = sessionmaker(bind=_engine)
    db = _Session()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture()
def repo(db_session: DbSession) -> SessionRepository:
    """SessionRepository backed by the fixture database session."""
    return SessionRepository(db_session)


def _make_session(
    *,
    owner: str = "alice",
    name: str = "Test session",
    archived: bool = False,
    endpoint_url: str = "http://localhost:11434",
    model: str = "llama3",
) -> ChatSession:
    """Create a minimal ChatSession ORM instance (not yet persisted)."""
    return ChatSession(
        id=str(uuid.uuid4()),
        name=name,
        endpoint_url=endpoint_url,
        model=model,
        owner=owner,
        rag=False,
        archived=archived,
        headers={},
    )


# ---------------------------------------------------------------------------
# save
# ---------------------------------------------------------------------------

class TestSave:
    def test_saves_new_session_and_returns_it(self, repo: SessionRepository) -> None:
        s = _make_session(name="New chat")
        saved = repo.save(s)
        assert saved.id == s.id
        assert saved.name == "New chat"

    def test_assigns_id_when_missing(self, repo: SessionRepository) -> None:
        s = _make_session()
        s.id = ""  # type: ignore[assignment]
        saved = repo.save(s)
        assert saved.id  # non-empty string
        assert len(saved.id) == 36  # UUID4 format

    def test_update_existing_session(
        self, repo: SessionRepository, db_session: DbSession
    ) -> None:
        s = _make_session(name="Original")
        repo.save(s)
        # Update via direct query to avoid ORM attribute-assignment type ambiguity.
        db_session.query(ChatSession).filter(ChatSession.id == s.id).update(
            {"name": "Renamed"}, synchronize_session="fetch"
        )
        db_session.flush()
        db_session.expire(s)  # force reload on next access
        updated = repo.get(s.id)
        assert updated is not None
        assert updated.name == "Renamed"


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------

class TestGet:
    def test_get_saved_session(self, repo: SessionRepository) -> None:
        s = _make_session()
        repo.save(s)
        found = repo.get(s.id)
        assert found is not None
        assert found.id == s.id

    def test_get_missing_returns_none(self, repo: SessionRepository) -> None:
        assert repo.get("00000000-0000-0000-0000-000000000000") is None


# ---------------------------------------------------------------------------
# list / list_by_user
# ---------------------------------------------------------------------------

class TestList:
    def test_list_by_user_returns_only_owner_sessions(
        self, repo: SessionRepository
    ) -> None:
        alice_s = _make_session(owner="alice", name="Alice's chat")
        bob_s = _make_session(owner="bob", name="Bob's chat")
        repo.save(alice_s)
        repo.save(bob_s)

        alice_sessions = repo.list_by_user("alice")
        assert all(s.owner == "alice" for s in alice_sessions)
        assert any(s.id == alice_s.id for s in alice_sessions)
        assert all(s.id != bob_s.id for s in alice_sessions)

    def test_list_by_user_empty_for_unknown_owner(
        self, repo: SessionRepository
    ) -> None:
        assert repo.list_by_user("nobody") == []

    def test_list_includes_archived_sessions(self, repo: SessionRepository) -> None:
        active = _make_session(owner="carol", archived=False)
        archived = _make_session(owner="carol", archived=True)
        repo.save(active)
        repo.save(archived)

        all_sessions = repo.list_by_user("carol")
        ids = {s.id for s in all_sessions}
        assert active.id in ids
        assert archived.id in ids

    def test_list_unknown_filter_raises_typeerror(
        self, repo: SessionRepository
    ) -> None:
        with pytest.raises(TypeError, match="does not support filter"):
            repo.list(title="test")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# get_active
# ---------------------------------------------------------------------------

class TestGetActive:
    def test_excludes_archived_sessions(self, repo: SessionRepository) -> None:
        active = _make_session(owner="dave", archived=False)
        archived = _make_session(owner="dave", archived=True)
        repo.save(active)
        repo.save(archived)

        active_sessions = repo.get_active("dave")
        ids = {s.id for s in active_sessions}
        assert active.id in ids
        assert archived.id not in ids

    def test_empty_when_all_archived(self, repo: SessionRepository) -> None:
        s = _make_session(owner="eve", archived=True)
        repo.save(s)
        assert repo.get_active("eve") == []


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------

class TestDelete:
    def test_delete_existing_session_returns_true(
        self, repo: SessionRepository
    ) -> None:
        s = _make_session()
        repo.save(s)
        assert repo.delete(s.id) is True
        assert repo.get(s.id) is None

    def test_delete_missing_session_returns_false(
        self, repo: SessionRepository
    ) -> None:
        assert repo.delete("00000000-0000-0000-0000-000000000000") is False

    def test_delete_is_idempotent(self, repo: SessionRepository) -> None:
        s = _make_session()
        repo.save(s)
        repo.delete(s.id)
        # Second delete must not raise
        assert repo.delete(s.id) is False


# ---------------------------------------------------------------------------
# archive
# ---------------------------------------------------------------------------

class TestArchive:
    def test_archive_sets_archived_flag(self, repo: SessionRepository) -> None:
        s = _make_session(archived=False)
        repo.save(s)
        ok = repo.archive(s.id)
        assert ok is True
        found = repo.get(s.id)
        assert found is not None
        assert found.archived is True

    def test_archive_missing_returns_false(self, repo: SessionRepository) -> None:
        assert repo.archive("00000000-0000-0000-0000-000000000000") is False


# ---------------------------------------------------------------------------
# touch (last_accessed)
# ---------------------------------------------------------------------------

class TestTouch:
    def test_touch_updates_last_accessed(
        self, repo: SessionRepository, db_session: DbSession
    ) -> None:
        from datetime import datetime

        s = _make_session()
        repo.save(s)
        # Force last_accessed to a known old value via a direct UPDATE to avoid
        # SQLAlchemy ORM attribute-assignment typing ambiguity in tests.
        db_session.query(ChatSession).filter(ChatSession.id == s.id).update(
            {"last_accessed": datetime(2020, 1, 1)}, synchronize_session="fetch"
        )
        db_session.flush()

        repo.touch(s.id)

        refreshed = repo.get(s.id)
        assert refreshed is not None
        assert refreshed.last_accessed is not None
        # Should be within the last minute
        now = datetime.now()
        delta = abs((refreshed.last_accessed - now).total_seconds())
        assert delta < 60

    def test_touch_missing_returns_false(self, repo: SessionRepository) -> None:
        assert repo.touch("00000000-0000-0000-0000-000000000000") is False
