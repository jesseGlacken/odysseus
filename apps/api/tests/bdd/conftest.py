"""Shared BDD fixtures for the auth domain.

Builds a minimal FastAPI app that mounts *only* the auth router so tests
run without dragging in the full app.py startup sequence.
"""

import os
import shutil
import tempfile
from collections.abc import Generator

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

# Set a temp data dir BEFORE importing any src.constants-dependent module.
_DATA_DIR = tempfile.mkdtemp(prefix="odysseus_bdd_")
os.environ["ODYSSEUS_DATA_DIR"] = _DATA_DIR

from core.auth import AuthManager  # noqa: E402
from core.constants import AUTH_FILE, SESSIONS_FILE  # noqa: E402
from routes.auth_routes import setup_auth_routes  # noqa: E402


def _reset_auth_files() -> None:
    """Wipe persisted auth and session state so each test starts clean."""
    for path in (AUTH_FILE, SESSIONS_FILE):
        if os.path.exists(path):
            os.remove(path)


@pytest.fixture
def auth_manager() -> Generator[AuthManager, None, None]:
    """Fresh AuthManager with isolated auth + session files."""
    _reset_auth_files()
    manager = AuthManager()
    manager._sessions.clear()
    manager._save_sessions()
    yield manager
    _reset_auth_files()


@pytest.fixture
def app(auth_manager: AuthManager) -> FastAPI:
    """Minimal FastAPI app that mounts *only* the auth router."""
    fast_app = FastAPI()
    fast_app.include_router(setup_auth_routes(auth_manager))
    return fast_app


@pytest.fixture
def client(app: FastAPI) -> Generator[TestClient, None, None]:
    """HTTP test client for black-box auth scenarios."""
    with TestClient(app) as tc:
        yield tc


def pytest_sessionfinish() -> None:
    """Clean up the temp data directory after the test session."""
    shutil.rmtree(_DATA_DIR, ignore_errors=True)
