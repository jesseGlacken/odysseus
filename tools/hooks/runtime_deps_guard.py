#!/usr/bin/env python3
"""Pre-commit hook: check that runtime requirements don't include test-only deps.

ADR-0004 mandates separating test dependencies from runtime. This hook fails
(advisory) if pytest, pytest-asyncio, or httpx2 appear in the runtime
requirements file.
"""

import sys

TEST_DEPS = {"pytest", "pytest-asyncio", "httpx2"}


def check_requirements(path: str) -> list[str]:
    """Return list of test dependencies found in the requirements file."""
    found: list[str] = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Extract package name (before any version specifier or extras)
            pkg = line.split(">")[0].split("<")[0].split("=")[0].split("[")[0].split(";")[0].strip()
            if pkg.lower() in TEST_DEPS:
                found.append(pkg)
    return found


def main() -> int:
    exit_code = 0
    for path in sys.argv[1:]:
        found = check_requirements(path)
        if found:
            print(f"ADVISORY: {path} contains test-only dependencies: {', '.join(found)}")
            print(f"  These should be in [project.optional-dependencies] dev, not runtime requirements.")
            print(f"  See ADR-0004 and ODY-11.")
            exit_code = 1
        else:
            print(f"OK: {path} — no test deps in runtime requirements")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
