"""src.infra.repositories.settings_repository — Repository for application settings (ODY-71 / P2.3b).

Settings in Odysseus v1 are stored in ``data/settings.json`` via
``src.settings`` (load_settings / save_settings / get_setting).
This repository wraps those primitives so domain code can depend on
the ``SettingsRepository`` interface instead of on the internal
loader directly.
"""
from __future__ import annotations

from typing import Any

from src.infra.repositories.base import Repository


class SettingsRepository(Repository[dict]):
    """Repository for application settings backed by the JSON settings store.

    This is a key-value repository — *id* is a dot-separated setting key
    (e.g. ``"model.default_provider"``).  ``get()`` delegates to
    ``src.settings.get_setting`` which merges saved values with defaults.
    ``save()`` and ``delete()`` write through ``load_settings`` /
    ``save_settings``.
    """

    # Settings are global, not per-instance — the module-level functions
    # are sufficient.  The class exists for interface uniformity.

    def get(self, id: str) -> Any:  # noqa: A003
        from src.settings import get_setting

        return get_setting(id)

    def list(self, **filters: Any) -> list[dict]:  # noqa: A003
        if filters:
            raise TypeError("SettingsRepository.list() does not support filters")
        from src.settings import load_settings

        raw = load_settings()
        return [{"key": k, "value": v} for k, v in raw.items()]

    def save(self, entity: dict) -> dict:
        key = str(entity.get("key", ""))
        value = entity.get("value")
        if not key:
            raise ValueError("Settings key must not be empty")
        from src.settings import load_settings, save_settings

        current = load_settings()
        current[key] = value
        save_settings(current)
        return {"key": key, "value": value}

    def delete(self, id: str) -> bool:
        from src.settings import get_setting, load_settings, save_settings

        if get_setting(id) is None:
            return False
        current = load_settings()
        current.pop(id, None)
        save_settings(current)
        return True
