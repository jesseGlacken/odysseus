"""src.validators — shared input-validation helpers (ODY-22 / P2.4).

Extracted from routes/_validators.py so domain tools can validate inputs
without importing from routes/ (ADR-0001 layering).

routes/_validators.py re-exports these names for backward compatibility.
"""
from __future__ import annotations

import re

from fastapi import HTTPException

_REMOTE_HOST_RE = re.compile(
    r"^(?:[A-Za-z0-9][A-Za-z0-9._-]*@)?[A-Za-z0-9][A-Za-z0-9._-]*$"
)
_SSH_PORT_RE = re.compile(r"^\d{1,5}$")


def validate_remote_host(v: str | None) -> str | None:
    """Validate a remote host string (optionally user@host).

    Raises :class:`fastapi.HTTPException` 400 if the value is present but
    malformed. Returns ``None`` for absent/empty values (caller treats them as
    "no remote host configured").
    """
    if v is None or v == "":
        return None
    if not _REMOTE_HOST_RE.match(v):
        raise HTTPException(
            400,
            "Invalid remote_host — must be host or user@host, no SSH option syntax",
        )
    return v


def validate_ssh_port(v: str | None) -> str | None:
    """Validate an SSH port string.

    Raises :class:`fastapi.HTTPException` 400 if the value is present but
    out of range or non-numeric. Returns ``None`` for absent/empty values.
    """
    if v is None or v == "":
        return None
    if not _SSH_PORT_RE.fullmatch(str(v)):
        raise HTTPException(400, "Invalid ssh_port")
    port = int(v)
    if port < 1 or port > 65535:
        raise HTTPException(400, "Invalid ssh_port")
    return str(port)
