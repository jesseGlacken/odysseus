"""User preferences API — per-user key/value store backed by a JSON file."""
from fastapi import APIRouter, Request
from src.auth_helpers import get_current_user

# Re-export shared prefs helpers from src.prefs_helpers so that any code that
# previously imported these from routes.prefs_routes continues to work, while
# new code can import from src.prefs_helpers directly (ODY-22 / P2.4).
from src.prefs_helpers import _load, _save, _load_for_user, _save_for_user  # noqa: F401


def setup_prefs_routes():
    router = APIRouter(prefix="/api/prefs", tags=["preferences"])

    @router.get("")
    async def get_all_prefs(request: Request):
        user = get_current_user(request)
        return _load_for_user(user)

    @router.get("/{key}")
    async def get_pref(request: Request, key: str):
        user = get_current_user(request)
        prefs = _load_for_user(user)
        return {"key": key, "value": prefs.get(key)}

    @router.put("/{key}")
    async def set_pref(request: Request, key: str, body: dict):
        user = get_current_user(request)
        prefs = _load_for_user(user)
        prefs[key] = body.get("value")
        _save_for_user(user, prefs)
        return {"key": key, "value": prefs[key]}

    return router
