"""src.cookbook_helpers — shared cookbook utilities (ODY-22 / P2.4).

Extracted from routes/cookbook_helpers.py so tool implementations can load
stored tokens without importing from routes/ (ADR-0001 layering).

routes/cookbook_helpers.py re-exports these names for backward compatibility.
"""
from __future__ import annotations

import json
import os
from pathlib import Path


def load_stored_hf_token(*, state_path: Path | str | None = None) -> str:
    """Return the decrypted HuggingFace token from cookbook_state.json.

    Falls back to the ``HF_TOKEN`` / ``HUGGING_FACE_HUB_TOKEN`` environment
    variables when the state file is absent or the token field is empty.

    Parameters
    ----------
    state_path:
        Override the location of ``cookbook_state.json``. Defaults to
        ``$DATA_DIR/cookbook_state.json`` (or ``data/cookbook_state.json``
        when ``DATA_DIR`` is not set).

    Returns
    -------
    str
        The decrypted token, or an empty string when no token is configured.
    """
    path = (
        Path(state_path)
        if state_path
        else Path(os.environ.get("DATA_DIR", "data")) / "cookbook_state.json"
    )
    token = ""
    if path.exists():
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
            env = state.get("env") if isinstance(state, dict) else {}
            if isinstance(env, dict) and env.get("hfToken"):
                from src.secret_storage import decrypt
                token = decrypt(env.get("hfToken") or "")
        except Exception:
            token = ""
    if not token:
        token = (
            os.environ.get("HF_TOKEN")
            or os.environ.get("HUGGING_FACE_HUB_TOKEN")
            or ""
        ).strip()
    return token
