#!/usr/bin/env python3
"""Pre-commit hook: check that FastAPI route decorators have response_model.

ADR-0001 mandates contract-first API — every endpoint must declare a typed
response_model. This hook scans route files for @router.<verb> decorators
that are missing the response_model parameter.

Blocking for domains marked "clean" in tools/hooks/domain_registry.json.
Advisory (warning only) for pending/in-progress domains.
"""

import ast
import json
import sys
from pathlib import Path

ROUTER_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}

HOOK_DIR = Path(__file__).resolve().parent
REGISTRY_PATH = HOOK_DIR / "domain_registry.json"


def load_registry() -> dict:
    """Load the domain registry or return safe defaults."""
    try:
        return json.loads(REGISTRY_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {"clean": [], "in_progress": [], "pending": []}


def domain_from_path(path: str) -> str:
    """Extract the domain name from a route file path (e.g. auth, chat, email)."""
    stem = Path(path).stem
    # Map route file names to domain names
    domain_map = {
        "auth_routes": "auth",
        "chat_routes": "chat",
        "document_routes": "documents",
        "email_routes": "email",
        "calendar_routes": "calendar",
        "gallery_routes": "gallery",
        "cookbook_routes": "cookbook",
        "note_routes": "notes",
        "research_routes": "research",
        "session_routes": "session",
        "prefs_routes": "prefs",
        "admin_wipe_routes": "admin",
        "history_routes": "history",
        "memory_routes": "memory",
        "shell_routes": "shell",
        "codex_routes": "codex",
        "model_routes": "model",
    }
    for key, domain in domain_map.items():
        if key in stem:
            return domain
    return stem


def check_file(path: str) -> list[str]:
    """Return list of violations (route:lineno missing response_model)."""
    violations: list[str] = []
    try:
        tree = ast.parse(Path(path).read_text())
    except SyntaxError as e:
        return [f"{path}: syntax error — {e}"]

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute):
            continue
        if not isinstance(node.func.value, ast.Name):
            continue
        if node.func.value.id != "router":
            continue
        if node.func.attr not in ROUTER_METHODS:
            continue

        # Check for response_model or openapi_extra (for SSE endpoints)
        has_response_model = False
        has_openapi_extra = False
        for kw in node.keywords:
            if kw.arg == "response_model":
                has_response_model = True
            if kw.arg == "openapi_extra":
                has_openapi_extra = True

        if not has_response_model and not has_openapi_extra:
            violations.append(
                f"{path}:{node.lineno} — @router.{node.func.attr}() missing response_model or openapi_extra"
            )

    return violations


def main() -> int:
    registry = load_registry()
    clean_domains = set(registry.get("clean", []))
    exit_code = 0

    for path in sys.argv[1:]:
        violations = check_file(path)
        domain = domain_from_path(path)
        is_clean = domain in clean_domains

        if violations:
            prefix = "BLOCKING" if is_clean else "ADVISORY"
            for v in violations:
                print(f"{prefix}: {v} (domain: {domain}, clean={is_clean})")
            if is_clean:
                exit_code = 1  # Fail for clean domains
        else:
            print(f"OK: {path} — all route decorators typed (domain: {domain})")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
