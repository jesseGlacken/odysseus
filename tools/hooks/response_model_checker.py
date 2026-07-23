#!/usr/bin/env python3
"""Pre-commit hook: check that FastAPI route decorators have response_model.

ADR-0001 mandates contract-first API — every endpoint must declare a typed
response_model. This hook scans route files for @router.<verb> decorators
that are missing the response_model parameter.

Advisory only during Phase 0.
"""

import ast
import sys
from pathlib import Path

ROUTER_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}


def check_file(path: str) -> list[str]:
    """Return list of violations (route:lineno missing response_model)."""
    violations: list[str] = []
    try:
        tree = ast.parse(Path(path).read_text())
    except SyntaxError as e:
        return [f"{path}: syntax error — {e}"]

    for node in ast.walk(tree):
        # Look for @router.<method>(...) decorators
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

        # Check if response_model is in kwargs
        has_response_model = False
        for kw in node.keywords:
            if kw.arg == "response_model":
                has_response_model = True
                break

        if not has_response_model:
            violations.append(f"{path}:{node.lineno} — @router.{node.func.attr}() missing response_model")

    return violations


def main() -> int:
    exit_code = 0
    for path in sys.argv[1:]:
        violations = check_file(path)
        if violations:
            for v in violations:
                print(f"ADVISORY: {v}")
            exit_code = 1
        else:
            print(f"OK: {path} — all route decorators have response_model (or no routes found)")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
