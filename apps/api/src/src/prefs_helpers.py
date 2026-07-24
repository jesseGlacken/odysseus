"""src.prefs_helpers — per-user preferences persistence (ODY-22 / P2.4).

Extracted from routes/prefs_routes.py so domain code can import prefs
utilities without violating the src/ → routes/ layering rule
(ADR-0001: domain code must not import from routes/).

routes/prefs_routes.py re-exports these names for backward compatibility
so the route file itself still works without changes to its callers.

Usage::

    from src.prefs_helpers import _load_for_user, _save_for_user

    prefs = _load_for_user(owner) or {}
    prefs["key"] = value
    _save_for_user(owner, prefs)
"""
from __future__ import annotations

import json
import os
from typing import Optional

from src.constants import USER_PREFS_FILE

# Internal: single source of truth for the prefs file path.
_PREFS_FILE: str = USER_PREFS_FILE


def _load() -> dict:
    """Load the raw prefs file (internal helper — prefer _load_for_user)."""
    try:
        with open(_PREFS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save(prefs: dict) -> None:
    """Atomically persist *prefs* to the raw prefs file.

    Uses write-then-rename (tmp → final) so a crash mid-write never leaves a
    truncated or partially-written file.
    """
    os.makedirs(os.path.dirname(_PREFS_FILE) or ".", exist_ok=True)
    tmp = f"{_PREFS_FILE}.tmp.{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(prefs, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, _PREFS_FILE)


def _load_for_user(user: Optional[str] = None) -> dict:
    """Load preferences for *user*.

    Supports both the legacy flat format (single-user installs) and the
    multi-user ``{"_users": {"alice": {...}, "bob": {...}}}`` format.

    Parameters
    ----------
    user:
        The username to load prefs for. Pass ``None`` when auth is disabled
        (single-user mode) — this returns the first user's prefs so that the
        caller sees *something* even without a username in scope.

    Returns
    -------
    dict
        A *copy* of the stored prefs dict (never ``None``).
    """
    all_prefs = _load()
    if "_users" in all_prefs:
        if user is None:
            # Auth disabled: return first user's prefs for backward compat.
            users = all_prefs["_users"]
            return dict(next(iter(users.values()), {}))
        return dict(all_prefs["_users"].get(user, {}))
    # Legacy flat format — return as-is.
    return dict(all_prefs)


def _save_for_user(user: Optional[str], prefs: dict) -> None:
    """Persist *prefs* for *user*.

    Handles both legacy flat format and multi-user ``_users`` dict, preserving
    all other users' data when *user* is ``None`` (auth-disabled / single-user).

    Parameters
    ----------
    user:
        Username to write under. ``None`` means auth is disabled.
    prefs:
        The complete prefs dict for this user (overwrites previous value).
    """
    all_prefs = _load()
    if user is None:
        # Auth disabled. If the store is already multi-user (e.g. auth was
        # turned off on a deployment that previously ran multi-user), writing
        # *prefs* flat would overwrite the whole ``_users`` map and destroy
        # every other user's preferences. Instead write back into the same
        # (first) slot _load_for_user(None) reads from, preserving the others.
        if "_users" in all_prefs:
            users = all_prefs["_users"]
            first_key = next(iter(users), None)
            if first_key is not None:
                users[first_key] = prefs
                _save(all_prefs)
                return
        _save(prefs)
        return
    if "_users" not in all_prefs:
        all_prefs = {"_users": {}}
    all_prefs["_users"][user] = prefs
    _save(all_prefs)
