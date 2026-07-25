"""src.infra.repositories.user_repository — Repository for the User aggregate (ODY-20 / P2.3).

Users are stored in a JSON file (``data/auth.json``) managed by
``core.auth.AuthManager``, *not* in SQLAlchemy.  This repository wraps the
AuthManager so that domain code can depend on the ``UserRepository`` interface
instead of on ``core.auth`` directly.

The :class:`UserRecord` dataclass is the aggregate-root value object exchanged
between this repository and its callers.  It is frozen and self-contained —
no SQLAlchemy sessions, no file handles.

Design notes
------------
* ``save()`` is a low-level upsert that writes the ``UserRecord`` fields
  directly to the JSON store. Callers are responsible for providing a valid
  bcrypt hash in ``password_hash``.  For user-facing account creation, use
  :meth:`UserRepository.create_user`, which delegates password hashing to
  ``AuthManager.create_user``.
* ``delete()`` removes the record at the storage level without the
  ``requesting_user`` guard that ``AuthManager.delete_user`` enforces.  This
  is intentional: the repository is infrastructure; authorisation belongs in
  the service/route layer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from src.infra.repositories.base import Repository


@dataclass(frozen=True)
class UserRecord:
    """Typed view of a user row from the AuthManager JSON store.

    Attributes
    ----------
    username:
        Normalised (lowercase, stripped) username — the primary key.
    is_admin:
        Whether the user has admin privileges.
    created:
        Unix timestamp of when the account was created.
    privileges:
        Dict of per-feature boolean/int flags.  See
        ``core.auth.DEFAULT_PRIVILEGES`` for the canonical keys.
    password_hash:
        bcrypt hash of the user's password.  Excluded from ``repr()`` to
        prevent accidental leakage in logs.
    """

    username: str
    is_admin: bool
    created: float
    privileges: dict[str, Any]
    password_hash: str = field(repr=False, default="")

    @classmethod
    def _from_auth_dict(cls, username: str, data: dict[str, Any]) -> "UserRecord":
        """Build a ``UserRecord`` from a raw AuthManager user dict."""
        return cls(
            username=username,
            is_admin=bool(data.get("is_admin", False)),
            created=float(data.get("created", 0.0)),
            privileges=dict(data.get("privileges", {})),
            password_hash=str(data.get("password_hash", "")),
        )

    def _to_auth_dict(self) -> dict[str, Any]:
        """Serialise back to the AuthManager JSON format."""
        return {
            "password_hash": self.password_hash,
            "created": self.created,
            "is_admin": self.is_admin,
            "privileges": dict(self.privileges),
        }


class UserRepository(Repository[UserRecord]):
    """Repository for user accounts backed by ``core.auth.AuthManager``.

    Parameters
    ----------
    auth_manager:
        The ``AuthManager`` instance to wrap.  Inject a real one for
        production; pass one pointed at a temp directory for tests.
    """

    def __init__(self, auth_manager: Any) -> None:
        # Typed as ``Any`` to avoid a hard import of core.auth at module load
        # time; type checkers can treat it as ``AuthManager`` via TYPE_CHECKING.
        self._auth = auth_manager

    # ------------------------------------------------------------------
    # Repository[UserRecord] interface
    # ------------------------------------------------------------------

    def get(self, id: str) -> Optional[UserRecord]:
        """Return the ``UserRecord`` for *id* (the username), or ``None``."""
        return self.get_by_username(id)

    def list(self, **filters: Any) -> list[UserRecord]:  # noqa: A003
        """Return all users.

        No filters are currently supported — *filters* is accepted for
        interface compatibility and ignored.  A ``RuntimeError`` is raised for
        unknown filter keys so callers notice the mismatch early.
        """
        if filters:
            raise TypeError(
                f"UserRepository.list() does not support filters: {list(filters)}"
            )
        users = self._auth.users  # Dict[str, dict]
        return [
            UserRecord._from_auth_dict(uname, data)
            for uname, data in users.items()
        ]

    def save(self, entity: UserRecord) -> UserRecord:
        """Upsert *entity* into the auth store and return the persisted record.

        This is a low-level storage operation — it writes the ``UserRecord``
        fields (including ``password_hash``) directly to the JSON store.
        Business rules (reserved-username guard, password strength, etc.) are
        enforced by the service layer, not here.

        Parameters
        ----------
        entity:
            The ``UserRecord`` to persist.  ``entity.username`` must be a
            non-empty, already-normalised (lowercase/stripped) string.

        Raises
        ------
        ValueError:
            If ``entity.username`` is empty.
        """
        username = entity.username.strip().lower()
        if not username:
            raise ValueError("UserRecord.username must not be empty")

        with self._auth._config_lock:
            if "users" not in self._auth._config:
                self._auth._config["users"] = {}
            self._auth._config["users"][username] = entity._to_auth_dict()
            self._auth._save()
            # Capture inside the lock so the return value is consistent with
            # what was written, not a later state another thread might change.
            saved_data: dict[str, Any] = dict(self._auth._config["users"][username])

        return UserRecord._from_auth_dict(username, saved_data)

    def delete(self, id: str) -> bool:
        """Remove the user identified by *id* (the username).

        Returns ``True`` if the user existed and was deleted, ``False`` if not
        found.  No authorisation check is performed — that is the caller's
        responsibility.
        """
        username = id.strip().lower()
        with self._auth._config_lock:
            if username not in self._auth._config.get("users", {}):
                return False
            del self._auth._config["users"][username]
            self._auth._save()
        return True

    # ------------------------------------------------------------------
    # Domain-specific helpers
    # ------------------------------------------------------------------

    def get_by_username(self, username: str) -> Optional[UserRecord]:
        """Look up a user by username (case-insensitive).

        Equivalent to ``get(username)`` — provided as a named method for
        readability in service code.
        """
        key = username.strip().lower()
        data = self._auth.users.get(key)
        if data is None:
            return None
        return UserRecord._from_auth_dict(key, data)

    def exists(self, username: str) -> bool:
        """Return ``True`` iff *username* has a registered account."""
        return username.strip().lower() in self._auth.users

    def create_user(
        self,
        username: str,
        password: str,
        *,
        is_admin: bool = False,
    ) -> Optional[UserRecord]:
        """Create a new user account via ``AuthManager.create_user``.

        Password hashing and reserved-username guards are delegated to
        ``AuthManager``.  Returns the newly created ``UserRecord`` on
        success, or ``None`` if the username already exists or is invalid.

        Parameters
        ----------
        username:
            Desired username (normalised to lowercase).
        password:
            Plaintext password — will be bcrypt-hashed by AuthManager.
        is_admin:
            Grant admin privileges to the new account.
        """
        ok = self._auth.create_user(username, password, is_admin=is_admin)
        if not ok:
            return None
        key = username.strip().lower()
        data = self._auth.users.get(key)
        if data is None:
            return None  # shouldn't happen, but be safe
        return UserRecord._from_auth_dict(key, data)

    def set_admin(
        self,
        username: str,
        is_admin: bool,
        *,
        requesting_user: str,
    ) -> bool:
        """Promote or demote *username* to/from admin.

        Delegates to ``AuthManager.set_admin`` which enforces the
        "can't remove last admin" constraint.  Returns ``True`` on success.
        """
        from core.auth import SetAdminResult

        result = self._auth.set_admin(username, is_admin, requesting_user)
        return result is SetAdminResult.OK
