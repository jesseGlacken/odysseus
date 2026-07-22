# Odysseus v2 Refactoring Plan

**Plan created:** 2025-07-22  
**Baseline:** dev @ bda7f40  
**Target:** v2.0 major release  
**Approach:** Strangler migration (legacy keeps running until replacement passes gates)

---

## Executive Summary

This plan migrates Odysseus from a v1 FastAPI + vanilla-JS monolith to a v2 Nx polyglot monorepo with:
- Contract-first FastAPI backend (typed OpenAPI schema)
- React 19 + TypeScript SPA (shadcn/ui + React Aria)
- Black-box testing (Gherkin .feature files, 100% coverage, mutation testing)
- WCAG 2.2 AA accessibility gates

The migration is **stranger-style**: the legacy app keeps running while new components are built and validated. Nothing is deleted until its replacement passes all gates.

---

## Phase 0: Foundation & Guardrails (Weeks 1-4)

### Objective
Establish the Nx monorepo structure, relocate the backend into `apps/api/`, and scaffold advisory CI gates. The legacy app continues to run unchanged.

### Exit Criteria
- [ ] Nx workspace boots with `nx build api` and `nx serve api`
- [ ] Legacy app still runs via `python -m uvicorn app:app`
- [ ] CI gates are advisory (report-only, not blocking)
- [ ] ADRs, C4 diagrams, and Gherkin conventions documented
- [ ] OTel skeleton integrated (reuse `core/middleware.py`, `core/log_safety.py`)

---

### Step 0.1: Initialize Nx Workspace

**What:** Create the Nx workspace structure at the repo root.

**Files to create:**
```
nx.json
package.json (root, for Nx tooling)
.nxignore
```

**Commands:**
```bash
npm install -D nx @nx/js @nxlv/python
npx nx init --interactive=false --nxCloud=skip
```

**nx.json content:**
```json
{
  "affected": { "defaultBase": "main" },
  "targetDefaults": {
    "build": { "dependsOn": ["^build"], "cache": true },
    "test": { "dependsOn": ["^build"], "cache": true },
    "lint": { "cache": true },
    "e2e": { "dependsOn": ["^build"], "cache": true }
  },
  "plugins": [
    { "plugin": "@nxlv/python", "options": { "packageManager": "uv" } }
  ],
  "namedInputs": {
    "default": ["{projectRoot}/**/*", "sharedGlobals"],
    "production": [
      "default",
      "!{projectRoot}/**/*.spec.ts",
      "!{projectRoot}/**/*.test.ts",
      "!{projectRoot}/tests/**/*"
    ],
    "sharedGlobals": ["{workspaceRoot}/package.json"]
  }
}
```

**package.json (root):**
```json
{
  "name": "@odysseus/root",
  "version": "2.0.0",
  "private": true,
  "scripts": {
    "nx": "nx",
    "build": "nx run-many -t build",
    "test": "nx run-many -t test",
    "lint": "nx run-many -t lint",
    "typecheck": "nx run-many -t typecheck"
  },
  "devDependencies": {
    "nx": "^20.3.0",
    "@nx/js": "^20.3.0",
    "@nxlv/python": "^18.0.0",
    "typescript": "^5.6.0"
  }
}
```

**Dependencies:** None  
**Risk:** Low (additive change, legacy app untouched)  
**Validation:** `nx show projects` lists `api` (will be created in Step 0.2)

---

### Step 0.2: Relocate Backend into `apps/api/`

**What:** Move the Python backend from repo root into `apps/api/` with src-layout and a proper `pyproject.toml` with build-system.

**Files to move:**
```
app.py → apps/api/app.py
core/ → apps/api/core/
routes/ → apps/api/routes/
src/ → apps/api/src/
services/ → apps/api/services/
mcp_servers/ → apps/api/mcp_servers/
integrations/ → apps/api/integrations/
setup.py → apps/api/setup.py
requirements.txt → apps/api/requirements.txt
requirements-optional.txt → apps/api/requirements-optional.txt
```

**Files to create:**
```
apps/api/pyproject.toml (with build-system, src-layout)
apps/api/project.json (Nx project config)
apps/api/.python-version
apps/api/README.md
```

**apps/api/pyproject.toml:**
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "odysseus-api"
version = "2.0.0"
description = "Odysseus FastAPI backend"
readme = "README.md"
requires-python = ">=3.11"
license = { text = "MIT" }
authors = [
  { name = "Jesse Glacken", email = "jesserglacken@gmail.com" }
]
dependencies = [
  "fastapi>=0.115.0",
  "uvicorn[standard]>=0.32.0",
  "python-multipart>=0.0.12",
  "python-dotenv>=1.0.1",
  "httpx>=0.27.2",
  "httpcore>=1.0,<2.0",
  "pydantic>=2.13.4",
  "pydantic-settings>=2.14.1",
  "SQLAlchemy>=2.0.36",
  "pypdf>=5.1.0",
  "beautifulsoup4>=4.12.3",
  "charset-normalizer>=3.4.0",
  "numpy>=1.26.4",
  "chromadb-client>=0.5.20",
  "fastembed>=0.4.2",
  "youtube-transcript-api>=0.6.2",
  "markdown>=3.7.0",
  "nh3>=0.2.19",
  "icalendar>=6.0.1",
  "python-dateutil>=2.9.0",
  "caldav>=1.3.9",
  "cryptography>=43.0.3",
  "bcrypt>=4.2.0",
  "mcp>=1.0.0",
  "pyotp>=2.9.0",
  "qrcode[pil]>=7.4.2",
  "croniter>=2.0.7",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.3.4",
  "pytest-asyncio>=0.24.0",
  "pytest-cov>=5.0.0",
  "httpx2>=0.28.0",
  "ruff>=0.7.0",
  "mypy>=1.13.0",
  "radon>=3.3.2",
  "mutmut>=2.5.0",
  "vulture>=2.11",
  "pre-commit>=4.0.1",
]

[tool.hatch.build.targets.wheel]
packages = ["."]

[tool.pytest.ini_options]
testpaths = ["../../tests"]
asyncio_mode = "auto"
markers = [
  "area_security: tests covering auth, owner-scope, SSRF, XSS, confinement, redaction",
  "area_routes: tests covering HTTP route / API behavior",
  "area_services: tests covering service-layer behavior",
  "area_cli: tests covering CLI / script behavior",
  "area_js: JavaScript / Node-backed tests",
  "area_helpers: self-tests for the shared test helpers",
  "area_unit: pure parser / utility tests",
  "area_uncategorized: tests not yet matched by the taxonomy",
  "slow: opt-in marker for known-slow tests",
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "C4", "SIM", "PTH", "RUF"]
ignore = ["E501"]

[tool.mypy]
python_version = "3.11"
strict = true
warn_unused_configs = true
warn_unused_ignores = true
warn_return_any = true
warn_unreachable = true

[tool.coverage.run]
branch = true
source = ["apps/api"]
omit = ["*/tests/*", "*/conftest.py"]

[tool.coverage.report]
fail_under = 0  # Advisory until Phase 1 domain is clean
show_missing = true
exclude_lines = [
  "pragma: no cover",  # Advisory: will be banned in Phase 1
  "if TYPE_CHECKING:",
  "if __name__ == .__main__.:",
]
```

**apps/api/project.json:**
```json
{
  "name": "api",
  "root": "apps/api",
  "sourceRoot": "apps/api",
  "projectType": "application",
  "tags": ["scope:backend", "type:app"],
  "targets": {
    "build": {
      "executor": "@nxlv/python:run-commands",
      "options": {
        "commands": ["cd apps/api && uv sync"],
        "cwd": "apps/api"
      }
    },
    "serve": {
      "executor": "@nxlv/python:run-commands",
      "options": {
        "commands": [
          "cd apps/api && uv run uvicorn app:app --host 127.0.0.1 --port 7000 --reload"
        ],
        "cwd": "apps/api"
      }
    },
    "test": {
      "executor": "@nxlv/python:run-commands",
      "options": {
        "commands": ["cd apps/api && uv run pytest -q"],
        "cwd": "apps/api"
      }
    },
    "lint": {
      "executor": "@nxlv/python:run-commands",
      "options": {
        "commands": [
          "cd apps/api && uv run ruff check .",
          "cd apps/api && uv run mypy --strict ."
        ],
        "cwd": "apps/api"
      }
    }
  }
}
```

**Commands:**
```bash
mkdir -p apps/api
git mv app.py apps/api/
git mv core/ apps/api/
git mv routes/ apps/api/
git mv src/ apps/api/
git mv services/ apps/api/
git mv mcp_servers/ apps/api/
git mv integrations/ apps/api/
git mv setup.py apps/api/
git mv requirements.txt apps/api/
git mv requirements-optional.txt apps/api/

cd apps/api
uv venv
uv sync

cd ../..
nx serve api
# Open http://localhost:7000
```

**Dependencies:** Step 0.1  
**Risk:** Medium (file moves can break imports; verify all paths still resolve)  
**Validation:**
- `nx build api` succeeds
- `nx serve api` starts the app on :7000
- `nx test api` runs the test suite (may have failures, but framework works)

---

### Step 0.3: Create `packages/config/` with Shared Presets

**What:** Create the shared configuration package for ESLint, TypeScript, Tailwind, Vitest, and Ruff presets.

**Files to create:**
```
packages/config/
├── package.json
├── project.json
├── eslint-preset/
│   ├── index.js
│   └── package.json
├── tsconfig-preset/
│   ├── base.json
│   ├── react.json
│   └── package.json
├── tailwind-preset/
│   ├── tailwind.config.js
│   └── package.json
├── vitest-preset/
│   ├── setup.ts
│   └── package.json
└── ruff-preset/
    ├── ruff.toml
    └── README.md
```

**packages/config/package.json:**
```json
{
  "name": "@odysseus/config",
  "version": "2.0.0",
  "private": true,
  "type": "module",
  "exports": {
    "./eslint": "./eslint-preset/index.js",
    "./tsconfig/base": "./tsconfig-preset/base.json",
    "./tsconfig/react": "./tsconfig-preset/react.json",
    "./tailwind": "./tailwind-preset/tailwind.config.js",
    "./vitest/setup": "./vitest-preset/setup.ts"
  },
  "devDependencies": {
    "eslint": "^9.14.0",
    "typescript-eslint": "^8.15.0",
    "eslint-plugin-react-hooks": "^5.0.0",
    "eslint-plugin-jsx-a11y": "^6.10.2",
    "eslint-plugin-i18next": "^6.1.1",
    "eslint-plugin-testing-library": "^6.4.0",
    "typescript": "^5.6.0",
    "tailwindcss": "^3.4.15",
    "vitest": "^2.1.5",
    "@vitest/coverage-v8": "^2.1.5"
  }
}
```

**packages/config/tsconfig-preset/base.json:**
```json
{
  "$schema": "https://json.schemastore.org/tsconfig",
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "allowJs": true,
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "isolatedModules": true,
    "verbatimModuleSyntax": true,
    "forceConsistentCasingInFileNames": true
  }
}
```

**packages/config/tsconfig-preset/react.json:**
```json
{
  "extends": "./base.json",
  "compilerOptions": {
    "jsx": "react-jsx",
    "lib": ["ES2022", "DOM", "DOM.Iterable"]
  }
}
```

**packages/config/vitest-preset/setup.ts:**
```typescript
import '@testing-library/jest-dom/vitest';
import 'vitest-axe/extend-expect';
```

**packages/config/project.json:**
```json
{
  "name": "config",
  "root": "packages/config",
  "sourceRoot": "packages/config",
  "projectType": "library",
  "tags": ["scope:shared", "type:config"],
  "targets": {
    "lint": {
      "executor": "@nx/js:lint",
      "options": {
        "lintCommand": "eslint ."
      }
    }
  }
}
```

**Dependencies:** Step 0.1  
**Risk:** Low (additive, no impact on legacy)  
**Validation:** `nx show projects` lists `config`

---

### Step 0.4: Scaffold Advisory CI Gates

**What:** Create pre-commit hooks and update GitHub Actions to run advisory gates (report-only, not blocking).

**Files to create:**
```
.pre-commit-config.yaml
.github/workflows/quality-gates.yml
tools/hooks/
├── response_model_checker.py
├── openapi_drift.py
├── sdk_regen_drift.py
├── no_raw_fetch.py
├── black_box_heuristic.py
└── runtime_deps_guard.py
```

**.pre-commit-config.yaml:**
```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-toml
      - id: check-merge-conflict
      - id: detect-private-key
      - id: check-ast
  
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.21.2
    hooks:
      - id: gitleaks
  
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.7.4
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
        continue-on-error: true  # Advisory
  
  - repo: local
    hooks:
      - id: forbid-coverage-pragmas
        name: Forbid coverage pragmas
        entry: grep -r "pragma: no cover" apps/api/ || exit 0
        language: system
        types: [python]
        continue-on-error: true
      
      - id: forbid-type-ignore
        name: Forbid type: ignore
        entry: grep -r "# type: ignore" apps/api/ || exit 0
        language: system
        types: [python]
        continue-on-error: true
      
      - id: runtime-deps-guard
        name: Test deps not in runtime requirements
        entry: python tools/hooks/runtime_deps_guard.py
        language: python
        files: requirements\.txt$
        continue-on-error: true
      
      - id: response-model-checker
        name: Check response_model on routes
        entry: python tools/hooks/response_model_checker.py
        language: python
        files: apps/api/routes/.*\.py$
        continue-on-error: true
```

**tools/hooks/runtime_deps_guard.py:**
```python
#!/usr/bin/env python3
"""Check that test-only deps are not in runtime requirements.txt."""
import sys
from pathlib import Path

TEST_ONLY_DEPS = {'pytest', 'pytest-asyncio', 'httpx2', 'pytest-cov', 'mutmut'}

def main():
    req_file = Path('apps/api/requirements.txt')
    if not req_file.exists():
        return 0
    
    violations = []
    for line in req_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#'):
            pkg = line.split('>=')[0].split('==')[0].split('<')[0].split('[')[0].strip()
            if pkg in TEST_ONLY_DEPS:
                violations.append(pkg)
    
    if violations:
        print(f"❌ Test-only deps found in runtime requirements: {', '.join(violations)}")
        return 1
    
    print("✓ No test-only deps in runtime requirements")
    return 0

if __name__ == '__main__':
    sys.exit(main())
```

**tools/hooks/response_model_checker.py:**
```python
#!/usr/bin/env python3
"""AST-based check: every @router.<verb> decorator must have response_model."""
import ast
import sys
from pathlib import Path

def check_file(path: Path) -> list[str]:
    violations = []
    try:
        tree = ast.parse(path.read_text())
    except SyntaxError:
        return [f"{path}: syntax error"]
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call):
                    if isinstance(decorator.func, ast.Attribute):
                        if decorator.func.attr in ('get', 'post', 'put', 'delete', 'patch'):
                            has_response_model = any(
                                kw.arg == 'response_model' for kw in decorator.keywords
                            )
                            if not has_response_model:
                                violations.append(
                                    f"{path}:{node.lineno} {node.name}() missing response_model"
                                )
    return violations

def main():
    routes_dir = Path('apps/api/routes')
    if not routes_dir.exists():
        return 0
    
    all_violations = []
    for py_file in routes_dir.rglob('*.py'):
        if py_file.name.startswith('__'):
            continue
        all_violations.extend(check_file(py_file))
    
    if all_violations:
        print(f"⚠️  {len(all_violations)} routes missing response_model (advisory):")
        for v in all_violations[:20]:
            print(f"  {v}")
        if len(all_violations) > 20:
            print(f"  ... and {len(all_violations) - 20} more")
        return 0  # Advisory
    
    print("✓ All routes have response_model")
    return 0

if __name__ == '__main__':
    sys.exit(main())
```

**.github/workflows/quality-gates.yml:**
```yaml
name: Quality Gates (Advisory)

on:
  pull_request:

permissions:
  contents: read

jobs:
  quality-gates:
    name: Quality gates (advisory)
    runs-on: ubuntu-latest
    continue-on-error: true
    
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
          persist-credentials: false
      
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
      
      - name: Install pre-commit
        run: pip install pre-commit
      
      - name: Run pre-commit (advisory)
        run: pre-commit run --all-files --show-diff-on-failure
        continue-on-error: true
      
      - name: Python type check (advisory)
        run: |
          cd apps/api
          pip install -r requirements.txt
          pip install mypy
          mypy --strict . || true
        continue-on-error: true
      
      - name: Python coverage report (advisory)
        run: |
          cd apps/api
          pip install pytest-cov
          pytest --cov=apps/api --cov-report=term-missing || true
        continue-on-error: true
      
      - name: Cyclomatic complexity report
        run: |
          pip install radon
          radon cc apps/api/ -s -a || true
        continue-on-error: true
```

**Commands:**
```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files

git add .pre-commit-config.yaml .github/workflows/quality-gates.yml tools/hooks/
git commit -m "chore: scaffold advisory quality gates"
```

**Dependencies:** Step 0.2  
**Risk:** Low (all gates are advisory)  
**Validation:**
- `pre-commit run --all-files` runs without failing (continue-on-error)
- CI workflow `quality-gates.yml` appears in GitHub Actions (may show warnings)

---

### Step 0.5: Remove Test Deps from Runtime Requirements

**What:** Move `pytest`, `pytest-asyncio`, and `httpx2` from `requirements.txt` to `[project.optional-dependencies] dev` in `pyproject.toml`.

**Files to modify:**
```
apps/api/requirements.txt
apps/api/pyproject.toml
```

**Changes to `apps/api/requirements.txt`:**
```diff
- pytest
- pytest-asyncio
- httpx2
```

**Commands:**
```bash
cd apps/api
uv sync
uv run uvicorn app:app --host 127.0.0.1 --port 7000

uv sync --all-extras
uv run pytest -q

git commit -m "refactor: move test deps to dev extras"
```

**Dependencies:** Step 0.4  
**Risk:** Low (test deps are only used in tests, not runtime)  
**Validation:**
- `uv run uvicorn app:app` starts successfully
- `uv run pytest -q` runs tests
- `pre-commit run runtime-deps-guard --all-files` passes

---

### Step 0.6: Document ADRs, C4 Diagrams, and Gherkin Conventions

**What:** Create C4 model diagrams and document Gherkin conventions for the team.

**Files to create:**
```
docs/c4/
├── context.puml (or .mmd for Mermaid)
├── container.puml
└── component.puml
docs/gherkin-conventions.md
```

**docs/gherkin-conventions.md:**
```markdown
# Gherkin Conventions

## File Structure
- Feature files live in `features/` (shared between backend and E2E)
- One `.feature` file per domain or user journey
- Use `Background:` for common setup steps

## Tagging
- `@api` — backend API test (pytest-bdd)
- `@e2e` — end-to-end test (playwright-bdd)
- `@smoke` — critical path (run on every PR)
- `@slow` — long-running (exclude from fast lane)
- `@a11y` — accessibility-specific test

## Step Definitions
- Backend: `tests/bdd/steps/` (pytest-bdd)
- E2E: `e2e/steps/` (playwright-bdd)

## Naming
- Feature files: `<domain>.feature` (e.g., `auth.feature`, `chat.feature`)
- Scenarios: imperative mood ("Log in with valid credentials")
- Steps: reusable, parameterized
```

**Dependencies:** None  
**Risk:** Low (documentation only)  
**Validation:** Team reviews and approves conventions

---

### Step 0.7: Integrate OTel Skeleton

**What:** Add OpenTelemetry instrumentation to the FastAPI app, reusing existing `core/middleware.py` and `core/log_safety.py`.

**Files to modify:**
```
apps/api/app.py (add OTel middleware)
apps/api/core/middleware.py (add OTel spans)
apps/api/pyproject.toml (add OTel deps)
```

**Changes to `apps/api/pyproject.toml`:**
```toml
[project]
dependencies = [
  # ... existing deps ...
  "opentelemetry-api>=1.28.0",
  "opentelemetry-sdk>=1.28.0",
  "opentelemetry-instrumentation-fastapi>=0.49b0",
  "opentelemetry-exporter-otlp-proto-http>=1.28.0",
]
```

**Changes to `apps/api/app.py`:**
```python
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
    provider = TracerProvider()
    exporter = OTLPSpanExporter()
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)
```

**Dependencies:** Step 0.2  
**Risk:** Low (OTel is opt-in via env var)  
**Validation:**
- Start app without `OTEL_EXPORTER_OTLP_ENDPOINT` → no OTel overhead
- Start app with `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318` → traces exported

---

### Phase 0 Git Strategy

**Branch:** `feat/phase-0-foundation`  
**Commits:**
```
chore: initialize Nx workspace
refactor: relocate backend into apps/api/
chore: create packages/config with shared presets
chore: scaffold advisory CI gates
refactor: move test deps to dev extras
docs: add C4 diagrams and Gherkin conventions
feat: integrate OTel skeleton
```

**PR:** `feat/phase-0-foundation` → `main`  
**Review focus:**
- Legacy app still runs via `nx serve api`
- No regressions in existing tests
- Advisory gates produce useful reports

---

### Phase 0 Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| File moves break imports | Medium | High | Run full test suite after move; fix any import errors |
| `uv` not installed on CI | Low | Medium | Add `uv` install step to CI workflow |
| Advisory gates too noisy | Medium | Low | Tune thresholds; keep `continue-on-error: true` |
| OTel adds latency | Low | Low | Gate on env var; disable by default |

---

## Phase 1: Contract-First Backend (Weeks 5-10)

### Objective
Add typed `response_model` to all 465 endpoints, emit and snapshot `openapi.json`, generate the TypeScript SDK, and write Gherkin .feature files as black-box API tests. Coverage climbs from 47.5% toward 100%.

### Exit Criteria
- [ ] Every endpoint declares a typed `response_model` (Pydantic v2)
- [ ] `openapi.json` is emitted and snapshot-tested in CI
- [ ] TypeScript SDK is generated and snapshot-tested
- [ ] Gherkin .feature files cover core domains (auth, chat, documents, email)
- [ ] Backend coverage ≥ 80% (routes layer ≥ 70%)
- [ ] Branch + mutation gates flip to blocking per domain as each goes green

---

### Step 1.1: Create `packages/contracts/` for OpenAPI Schema

**What:** Create the contracts package that holds the OpenAPI schema and snapshot tests.

**Files to create:**
```
packages/contracts/
├── package.json
├── project.json
├── openapi.json (generated, committed)
├── generate.js
├── tests/
│   └── openapi-snapshot.test.ts
└── README.md
```

**packages/contracts/package.json:**
```json
{
  "name": "@odysseus/contracts",
  "version": "2.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "generate": "node generate.js",
    "test": "vitest run",
    "test:snapshot": "vitest run --update"
  },
  "devDependencies": {
    "vitest": "^2.1.5",
    "@vitest/coverage-v8": "^2.1.5"
  }
}
```

**packages/contracts/generate.js:**
```javascript
#!/usr/bin/env node
import { spawn } from 'node:child_process';
import { writeFileSync } from 'node:fs';
import { join } from 'node:path';

const app = spawn('uv', ['run', 'python', '-c', `
import json
from app import app
schema = app.openapi()
print(json.dumps(schema, indent=2))
`], {
  cwd: join(process.cwd(), 'apps/api'),
  stdio: ['ignore', 'pipe', 'inherit'],
});

let output = '';
app.stdout.on('data', (chunk) => {
  output += chunk;
});

app.on('close', (code) => {
  if (code !== 0) {
    console.error('Failed to generate OpenAPI schema');
    process.exit(1);
  }
  
  const outPath = join(process.cwd(), 'packages/contracts/openapi.json');
  writeFileSync(outPath, output, 'utf-8');
  console.log(`✓ Generated ${outPath}`);
});
```

**packages/contracts/tests/openapi-snapshot.test.ts:**
```typescript
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

describe('OpenAPI schema', () => {
  it('matches the committed snapshot', () => {
    const schemaPath = join(__dirname, '../openapi.json');
    const schema = JSON.parse(readFileSync(schemaPath, 'utf-8'));
    
    expect(schema).toMatchSnapshot();
    expect(schema.openapi).toMatch(/^3\./);
    expect(schema.info.title).toBe('Odysseus API');
    expect(Object.keys(schema.paths).length).toBeGreaterThan(400);
  });
  
  it('has no endpoints without response_model', () => {
    const schemaPath = join(__dirname, '../openapi.json');
    const schema = JSON.parse(readFileSync(schemaPath, 'utf-8'));
    
    const violations: string[] = [];
    
    for (const [path, methods] of Object.entries(schema.paths)) {
      for (const [method, spec] of Object.entries(methods as any)) {
        if (['get', 'post', 'put', 'delete', 'patch'].includes(method)) {
          const responses = spec.responses;
          if (!responses || !responses['200']) {
            violations.push(`${method.toUpperCase()} ${path} missing 200 response`);
          }
        }
      }
    }
    
    expect(violations, violations.join('\n')).toEqual([]);
  });
});
```

**packages/contracts/project.json:**
```json
{
  "name": "contracts",
  "root": "packages/contracts",
  "sourceRoot": "packages/contracts",
  "projectType": "library",
  "tags": ["scope:shared", "type:contracts"],
  "targets": {
    "generate": {
      "executor": "nx:run-commands",
      "options": {
        "commands": ["node generate.js"],
        "cwd": "packages/contracts"
      }
    },
    "test": {
      "executor": "@nx/vite:test",
      "options": {
        "config": "packages/contracts/vitest.config.ts"
      }
    }
  }
}
```

**Commands:**
```bash
cd packages/contracts
node generate.js
npm test

git add openapi.json tests/__snapshots__/
git commit -m "feat(contracts): add OpenAPI schema and snapshot test"
```

**Dependencies:** Step 0.2  
**Risk:** Low (additive, schema is generated)  
**Validation:**
- `nx generate contracts` produces `openapi.json`
- `nx test contracts` passes (snapshot matches)

---

### Step 1.2: Create `packages/client-sdk/` for Generated TypeScript Client

**What:** Generate a typed TypeScript client from the OpenAPI schema.

**Files to create:**
```
packages/client-sdk/
├── package.json
├── project.json
├── src/
│   ├── index.ts (re-export generated client)
│   └── generated/ (generated, gitignored)
├── generate.js
└── tests/
    └── sdk-snapshot.test.ts
```

**packages/client-sdk/package.json:**
```json
{
  "name": "@odysseus/client-sdk",
  "version": "2.0.0",
  "private": true,
  "type": "module",
  "main": "./src/index.ts",
  "types": "./src/index.ts",
  "scripts": {
    "generate": "node generate.js",
    "test": "vitest run"
  },
  "dependencies": {
    "openapi-fetch": "^0.1.0"
  },
  "devDependencies": {
    "openapi-typescript": "^7.4.3",
    "vitest": "^2.1.5"
  }
}
```

**packages/client-sdk/generate.js:**
```javascript
#!/usr/bin/env node
import { execSync } from 'node:child_process';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';

const schemaPath = join(process.cwd(), '../contracts/openapi.json');
const schema = readFileSync(schemaPath, 'utf-8');

const outDir = join(process.cwd(), 'src/generated');
mkdirSync(outDir, { recursive: true });

execSync(`npx openapi-typescript ${schemaPath} -o ${outDir}/schema.d.ts`, {
  stdio: 'inherit',
});

const clientCode = `
// Auto-generated — do not edit
import createClient from 'openapi-fetch';
import type { paths } from './schema';

export const client = createClient<paths>({ baseUrl: '/api' });
export * from './schema';
`;

writeFileSync(join(outDir, 'client.ts'), clientCode, 'utf-8');

console.log('✓ Generated TypeScript SDK');
```

**packages/client-sdk/src/index.ts:**
```typescript
export * from './generated/client';
```

**packages/client-sdk/.gitignore:**
```
src/generated/
```

**packages/client-sdk/project.json:**
```json
{
  "name": "client-sdk",
  "root": "packages/client-sdk",
  "sourceRoot": "packages/client-sdk/src",
  "projectType": "library",
  "tags": ["scope:shared", "type:sdk"],
  "targets": {
    "generate": {
      "executor": "nx:run-commands",
      "options": {
        "commands": ["node generate.js"],
        "cwd": "packages/client-sdk"
      },
      "dependsOn": ["^generate"]
    },
    "test": {
      "executor": "@nx/vite:test",
      "options": {
        "config": "packages/client-sdk/vitest.config.ts"
      }
    }
  }
}
```

**Commands:**
```bash
cd packages/client-sdk
npm run generate
npm test

git add package.json project.json src/index.ts tests/
git commit -m "feat(client-sdk): add generated TypeScript client"
```

**Dependencies:** Step 1.1  
**Risk:** Low (generated code, gitignored)  
**Validation:**
- `nx generate client-sdk` produces `src/generated/schema.d.ts` and `client.ts`
- `nx test client-sdk` passes

---

### Step 1.3: Add Typed Response Models (Domain by Domain)

**What:** Add Pydantic v2 `response_model` to all endpoints, starting with the auth domain, then chat, documents, email, etc.

**Approach:**
- Work one domain at a time (auth → chat → documents → email → ...)
- For each domain:
  1. Create response models in `apps/api/routes/<domain>/models.py`
  2. Add `response_model=ResponseModel` to each endpoint
  3. Regenerate `openapi.json` and verify snapshot diff
  4. Write Gherkin .feature file for the domain
  5. Run black-box tests and coverage
  6. Flip gates to blocking for that domain

**Example: Auth Domain**

**Files to create:**
```
apps/api/routes/auth_models.py
features/auth.feature
tests/bdd/steps/auth_steps.py
```

**apps/api/routes/auth_models.py:**
```python
"""Pydantic models for auth endpoints."""
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    token: str = Field(..., description="Session token")
    expires_at: int = Field(..., description="Unix timestamp")
    user: dict = Field(..., description="User profile")


class LogoutResponse(BaseModel):
    success: bool = True


class MeResponse(BaseModel):
    username: str
    is_admin: bool
    privileges: list[str]
```

**Changes to `apps/api/routes/auth_routes.py`:**
```python
from routes.auth_models import LoginRequest, LoginResponse, MeResponse

@router.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    # ... existing implementation ...
    pass

@router.get("/auth/me", response_model=MeResponse)
async def get_me(user=Depends(get_current_user)):
    # ... existing implementation ...
    pass
```

**features/auth.feature:**
```gherkin
@api @smoke
Feature: User authentication
  As a user
  I want to log in and manage my session
  So that I can access my workspace securely

  Background:
    Given a user "alice" with password "secret123"

  Scenario: Successful login
    When I POST to /api/auth/login with:
      | username | alice     |
      | password | secret123 |
    Then the response status is 200
    And the response contains a session token
    And the response contains the user profile

  Scenario: Failed login (wrong password)
    When I POST to /api/auth/login with:
      | username | alice    |
      | password | wrongpw  |
    Then the response status is 401
    And the response contains an error message

  Scenario: Get current user
    Given I am logged in as "alice"
    When I GET /api/auth/me
    Then the response status is 200
    And the response contains:
      | username | alice |
```

**tests/bdd/steps/auth_steps.py:**
```python
"""Step definitions for auth.feature."""
from pytest_bdd import given, when, then, parsers
import httpx


@given(parsers.parse('a user "{username}" with password "{password}"'))
def create_user(test_client, username, password):
    response = test_client.post("/api/admin/users", json={
        "username": username,
        "password": password,
        "is_admin": False,
    })
    assert response.status_code in (200, 409)


@given(parsers.parse('I am logged in as "{username}"'))
def login_user(test_client, context, username):
    response = test_client.post("/api/auth/login", json={
        "username": username,
        "password": "secret123",
    })
    assert response.status_code == 200
    context["token"] = response.json()["token"]


@when(parsers.parse('I POST to {path} with:'))
def post_request(test_client, context, path, datatable):
    data = {row[0]: row[1] for row in datatable}
    context["response"] = test_client.post(path, json=data)


@when(parsers.parse('I GET {path}'))
def get_request(test_client, context, path):
    headers = {}
    if "token" in context:
        headers["Authorization"] = f"Bearer {context['token']}"
    context["response"] = test_client.get(path, headers=headers)


@then(parsers.parse('the response status is {status:d}'))
def check_status(context, status):
    assert context["response"].status_code == status


@then('the response contains a session token')
def check_token(context):
    data = context["response"].json()
    assert "token" in data
    assert len(data["token"]) > 0


@then('the response contains the user profile')
def check_user_profile(context):
    data = context["response"].json()
    assert "user" in data
    assert "username" in data["user"]
```

**Commands:**
```bash
cd packages/contracts
node generate.js
npm test

cd apps/api
uv run pytest -m "bdd" tests/bdd/steps/auth_steps.py
uv run pytest --cov=apps/api/routes/auth_routes tests/

git add apps/api/routes/auth_routes.py apps/api/routes/auth_models.py \
        features/auth.feature tests/bdd/steps/auth_steps.py \
        packages/contracts/openapi.json
git commit -m "feat(api): add typed response models for auth domain"
```

**Dependencies:** Step 1.1, Step 1.2  
**Risk:** High (465 endpoints is a lot of work; each domain requires careful modeling)  
**Mitigation:**
- Start with the simplest domains (auth, session, prefs)
- Use `src/request_models.py` as a starting point for request models
- Review each domain's models with the team before committing

**Validation:**
- `nx generate contracts` produces updated schema
- `nx test contracts` passes (snapshot updated intentionally)
- `nx test api` includes new BDD tests
- Coverage for the domain ≥ 90%

---

### Step 1.4: Flip Gates to Blocking (Per Domain)

**What:** As each domain goes green (all endpoints typed, tests passing, coverage ≥ 90%), flip the quality gates from advisory to blocking for that domain.

**Approach:**
- Use a `DOMAINS_CLEAN` environment variable or file to track which domains are clean
- Update `.pre-commit-config.yaml` to check only clean domains
- Update CI to fail if a clean domain regresses

**Files to modify:**
```
.pre-commit-config.yaml
.github/workflows/quality-gates.yml
tools/hooks/domain_registry.json
```

**tools/hooks/domain_registry.json:**
```json
{
  "clean": ["auth", "session", "prefs"],
  "in_progress": ["chat", "documents"],
  "pending": ["email", "calendar", "gallery", "cookbook", "notes", "research"]
}
```

**Changes to `.pre-commit-config.yaml`:**
```yaml
- id: response-model-checker
  name: Check response_model on routes
  entry: python tools/hooks/response_model_checker.py --domains auth,session,prefs
  language: python
  files: apps/api/routes/(auth|session|prefs).*\.py$
  # Remove continue-on-error for clean domains
```

**Dependencies:** Step 1.3 (repeated for each domain)  
**Risk:** Medium (premature blocking can stall development)  
**Mitigation:**
- Only flip a domain after all endpoints are typed and tests pass
- Keep a rollback plan (revert to advisory if blocking causes issues)

**Validation:**
- `pre-commit run response-model-checker --all-files` fails if a clean domain has an untyped endpoint
- CI fails if a clean domain regresses

---

### Phase 1 Git Strategy

**Branch:** `feat/phase-1-contract-first`  
**Commits (per domain):**
```
feat(api): add typed response models for <domain>
feat(contracts): regenerate OpenAPI schema
feat(features): add Gherkin scenarios for <domain>
test(api): add black-box tests for <domain>
chore: flip quality gates to blocking for <domain>
```

**PRs:** One PR per domain (e.g., `feat/auth-domain`, `feat/chat-domain`)  
**Review focus:**
- Response models are correct and complete
- Gherkin scenarios cover key user journeys
- Tests are black-box (no internal mocking)
- Coverage is ≥ 90% for the domain

---

### Phase 1 Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Response models are wrong (missing fields) | High | Medium | Review with team; use existing `request_models.py` as starting point |
| Gherkin scenarios are too vague | Medium | Low | Use concrete examples; review with product owner |
| Coverage stalls at 70% | Medium | High | Focus on the routes layer; delete unreachable code |
| Mutation testing reveals weak tests | High | Medium | Add stronger assertions; don't annotate away |
| Snapshot diffs are too large | Low | Low | Review diffs carefully; break into smaller PRs |

---

## Phase 2: Backend Decoupling & SOLID (Weeks 11-16)

### Objective
Decompose `stream_agent_loop` (CC=531) and `_stream_llm_inner` (CC=216), regroup the flat `src/` into domain packages, introduce a repository layer to invert `core.database` (DIP), and remove the 36 `src→routes` backward imports.

### Exit Criteria
- [ ] `stream_agent_loop` is decomposed into prompt/classifier/verifier/runaway/context submodules (CC < 50 each)
- [ ] `_stream_llm_inner` is decomposed (CC < 50)
- [ ] `src/` is regrouped into `domain/`, `agent/`, `infra/`, `llm/` packages
- [ ] Repository layer introduced (no direct `core.database` calls from domain code)
- [ ] All 36 `src→routes` imports removed
- [ ] `core/database.py` split by domain (last, after 56 importers are migrated)
- [ ] No God modules (all files < 1,000 LOC)
- [ ] Cyclomatic complexity: no function > CC 50
- [ ] Coverage ≥ 90% overall, routes ≥ 80%

---

### Step 2.1: Decompose `stream_agent_loop`

**What:** Break `src/agent_loop.py` (4,529 LOC, `stream_agent_loop` CC=531) into focused submodules.

**Target structure:**
```
apps/api/src/agent/
├── __init__.py
├── loop.py (orchestrator, CC < 30)
├── prompt.py (build system prompt, CC < 30)
├── classifier.py (classify intent, CC < 20)
├── verifier.py (verify tool calls, CC < 20)
├── runaway.py (detect runaway loops, CC < 10)
└── context.py (manage context window, CC < 20)
```

**Approach:**
1. Extract `_build_system_prompt` (CC=115) into `prompt.py`
2. Extract intent classification logic into `classifier.py`
3. Extract tool-call verification into `verifier.py`
4. Extract runaway detection into `runaway.py`
5. Extract context-window management into `context.py`
6. Refactor `stream_agent_loop` to orchestrate these submodules (CC < 30)

**Commands:**
```bash
cd apps/api
uv run pytest tests/test_agent_loop.py
uv run radon cc src/agent/ -s
uv run radon cc src/agent/ -s | grep -E "CC [5-9][0-9]|CC [1-9][0-9]{2}"

git add src/agent/
git commit -m "refactor(agent): decompose stream_agent_loop into submodules"
```

**Dependencies:** Phase 1 (auth domain clean)  
**Risk:** High (core agent path, any bug breaks chat)  
**Mitigation:**
- Extract one submodule at a time
- Run the full test suite after each extraction
- Use feature flags to toggle between old and new implementations during rollout

**Validation:**
- `radon cc src/agent/loop.py` shows CC < 30 for `stream_agent_loop`
- All agent-related tests pass
- Manual smoke test: chat with the agent works

---

### Step 2.2: Regroup Flat `src/` into Domain Packages

**What:** Reorganize the flat `src/` (139 files) into domain packages.

**Target structure:**
```
apps/api/src/
├── __init__.py
├── domain/
│   ├── __init__.py
│   ├── auth/
│   ├── chat/
│   ├── documents/
│   ├── email/
│   ├── calendar/
│   ├── gallery/
│   ├── cookbook/
│   ├── notes/
│   └── research/
├── agent/
│   ├── __init__.py
│   ├── loop.py
│   ├── prompt.py
│   ├── classifier.py
│   ├── verifier.py
│   ├── runaway.py
│   └── context.py
├── infra/
│   ├── __init__.py
│   ├── config.py
│   ├── constants.py
│   ├── exceptions.py
│   ├── readiness.py
│   └── runtime_paths.py
└── llm/
    ├── __init__.py
    ├── core.py (decomposed from llm_core.py)
    ├── model_discovery.py
    ├── model_capabilities.py
    └── endpoint_resolver.py
```

**Approach:**
1. Create the new package structure
2. Move files one by one, updating imports
3. Add re-export shims in `src/__init__.py` to avoid breaking external imports
4. Run tests after each move

**Commands:**
```bash
cd apps/api/src
mkdir -p domain/auth domain/chat domain/documents
mkdir -p agent infra llm

git mv auth_helpers.py domain/auth/
git mv session_actions.py domain/auth/

uv run pytest -q

git commit -m "refactor(src): move auth files to domain/auth/"
```

**Dependencies:** Step 2.1  
**Risk:** High (139 files, many cross-imports)  
**Mitigation:**
- Move files in small batches (one domain at a time)
- Use re-export shims to avoid breaking external imports
- Run the full test suite after each batch

**Validation:**
- All tests pass after each batch
- `nx lint api` passes (no import errors)
- No circular imports

---

### Step 2.3: Introduce Repository Layer

**What:** Introduce a repository layer to invert `core.database` (DIP). Domain code talks to repositories, not SQLAlchemy directly.

**Files to create:**
```
apps/api/src/infra/repositories/
├── __init__.py
├── base.py (abstract repository interface)
├── user_repository.py
├── session_repository.py
├── document_repository.py
├── email_repository.py
└── ... (one per domain)
```

**Commands:**
```bash
cd apps/api
uv run pytest -q

git add src/infra/repositories/
git commit -m "feat(infra): introduce repository layer"
```

**Dependencies:** Step 2.2  
**Risk:** High (56 files import `core.database`)  
**Mitigation:**
- Introduce repositories gradually (one domain at a time)
- Keep the old `core.database` calls working during migration
- Use dependency injection to swap implementations

**Validation:**
- Domain code no longer imports `core.database` directly
- All tests pass
- Coverage ≥ 90%

---

### Step 2.4: Remove `src→routes` Backward Imports

**What:** Remove the 36 backward imports from `src/` to `routes/`.

**Commands:**
```bash
cd apps/api
grep -rn "from routes" src/ --include="*.py"

uv run pytest -q

grep -rn "from routes" src/ --include="*.py"
# Should return nothing

git commit -m "refactor: remove src→routes backward imports"
```

**Dependencies:** Step 2.2  
**Risk:** Medium (some imports are deeply nested)  
**Mitigation:**
- Start with the easiest imports (e.g., helper functions)
- Tackle `src/builtin_actions.py` (13 imports) last

**Validation:**
- `grep -rn "from routes" apps/api/src/` returns nothing
- All tests pass
- No circular imports

---

### Step 2.5: Split `core/database.py` (Last)

**What:** Split `core/database.py` (2,562 LOC, 56-file fan-in) into domain-specific modules.

**Target structure:**
```
apps/api/core/
├── __init__.py
├── database.py (connection setup, session management)
├── models/
│   ├── __init__.py
│   ├── user.py
│   ├── session.py
│   ├── document.py
│   ├── email.py
│   ├── calendar.py
│   └── ... (one per domain)
└── helpers/
    ├── __init__.py
    └── ... (shared DB helpers)
```

**Commands:**
```bash
cd apps/api/core
mkdir -p models

uv run pytest -q

git commit -m "refactor(core): split database.py into domain models"
```

**Dependencies:** Step 2.3 (repository layer must be in place first)  
**Risk:** High (56 importers, any mistake breaks the app)  
**Mitigation:**
- Use re-export shims to avoid breaking imports
- Update importers one domain at a time
- Run the full test suite after each update

**Validation:**
- `core/database.py` is < 500 LOC
- All tests pass
- No import errors

---

### Phase 2 Git Strategy

**Branch:** `feat/phase-2-decoupling`  
**Commits:**
```
refactor(agent): decompose stream_agent_loop
refactor(src): regroup into domain packages
feat(infra): introduce repository layer
refactor: remove src→routes backward imports
refactor(core): split database.py into domain models
```

**PRs:** Multiple small PRs (one per step or sub-step)  
**Review focus:**
- No God modules (all files < 1,000 LOC)
- No function > CC 50
- No layering violations
- Coverage ≥ 90%

---

### Phase 2 Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Decomposing `stream_agent_loop` introduces bugs | High | High | Extract one submodule at a time; run full test suite |
| Regrouping `src/` breaks imports | High | Medium | Use re-export shims; update imports incrementally |
| Repository layer adds latency | Low | Medium | Profile; optimize hot paths |
| Splitting `database.py` causes import errors | Medium | High | Use re-exports; update importers gradually |

---

## Phase 3: Front-End Foundation (Weeks 17-22)

### Objective
Scaffold `apps/web/` (React 19 + Vite SPA) and `packages/ui/` (shadcn/ui + React Aria components), wire the generated SDK behind TanStack Query, and enforce Lighthouse + axe budgets in CI.

### Exit Criteria
- [ ] `apps/web/` is a React 19 + TypeScript + Vite SPA
- [ ] `packages/ui/` has accessible components (shadcn/ui + React Aria)
- [ ] TanStack Query wired to the generated SDK
- [ ] Light/dark theme support with Tailwind tokens
- [ ] Storybook + a11y addon for component development
- [ ] Every component ships with axe tests
- [ ] Gherkin .feature files for core UI (chat, documents, settings)
- [ ] Lighthouse a11y = 100, perf budget met on core routes
- [ ] Coverage ≥ 80% (component tests + E2E)

---

### Step 3.1: Scaffold `apps/web/`

**What:** Create the React 19 + TypeScript + Vite SPA.

**Files to create:**
```
apps/web/
├── index.html
├── package.json
├── project.json
├── vite.config.ts
├── tsconfig.json
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── routes/
│   │   ├── __root.tsx
│   │   ├── index.tsx
│   │   ├── chat.tsx
│   │   ├── documents.tsx
│   │   └── settings.tsx
│   ├── components/
│   ├── hooks/
│   ├── lib/
│   └── styles/
│       └── globals.css
└── public/
```

**apps/web/package.json:**
```json
{
  "name": "@odysseus/web",
  "version": "2.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest",
    "test:coverage": "vitest run --coverage",
    "storybook": "storybook dev -p 6006",
    "build-storybook": "storybook build",
    "lint": "eslint .",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "@tanstack/react-query": "^5.62.0",
    "@tanstack/react-router": "^1.92.0",
    "@odysseus/client-sdk": "workspace:*",
    "@odysseus/ui": "workspace:*"
  },
  "devDependencies": {
    "vite": "^6.0.0",
    "@vitejs/plugin-react": "^4.3.4",
    "typescript": "^5.6.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "vitest": "^2.1.5",
    "@vitest/coverage-v8": "^2.1.5",
    "@testing-library/react": "^16.0.1",
    "@testing-library/jest-dom": "^6.6.3",
    "vitest-axe": "^0.1.0",
    "axe-core": "^4.10.2",
    "@storybook/react-vite": "^8.4.4",
    "@storybook/addon-a11y": "^8.4.4",
    "@storybook/addon-essentials": "^8.4.4",
    "eslint": "^9.14.0",
    "typescript-eslint": "^8.15.0",
    "eslint-plugin-react-hooks": "^5.0.0",
    "eslint-plugin-jsx-a11y": "^6.10.2"
  }
}
```

**apps/web/vite.config.ts:**
```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:7000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          router: ['@tanstack/react-router'],
          query: ['@tanstack/react-query'],
        },
      },
    },
  },
});
```

**apps/web/tsconfig.json:**
```json
{
  "extends": "@odysseus/config/tsconfig/react",
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

**apps/web/src/main.tsx:**
```typescript
import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RouterProvider, createRouter } from '@tanstack/react-router';
import { routeTree } from './routeTree.gen';
import './styles/globals.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,
      retry: 1,
    },
  },
});

const router = createRouter({ routeTree });

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </React.StrictMode>
);
```

**apps/web/project.json:**
```json
{
  "name": "web",
  "root": "apps/web",
  "sourceRoot": "apps/web/src",
  "projectType": "application",
  "tags": ["scope:frontend", "type:app"],
  "targets": {
    "dev": {
      "executor": "@nx/vite:dev-server",
      "options": {
        "buildTarget": "web:build",
        "hmr": true
      }
    },
    "build": {
      "executor": "@nx/vite:build",
      "options": {
        "outputPath": "apps/web/dist"
      }
    },
    "test": {
      "executor": "@nx/vite:test",
      "options": {
        "config": "apps/web/vitest.config.ts"
      }
    },
    "lint": {
      "executor": "@nx/eslint:lint",
      "options": {
        "lintCommand": "eslint ."
      }
    },
    "typecheck": {
      "executor": "nx:run-commands",
      "options": {
        "commands": ["tsc --noEmit"],
        "cwd": "apps/web"
      }
    },
    "storybook": {
      "executor": "@nx/storybook:storybook",
      "options": {
        "port": 6006
      }
    }
  }
}
```

**Commands:**
```bash
cd apps/web
npm install
npm run dev

npm test

git add apps/web/
git commit -m "feat(web): scaffold React 19 + Vite SPA"
```

**Dependencies:** Step 1.2 (client-sdk must be generated)  
**Risk:** Low (additive, no impact on legacy)  
**Validation:**
- `nx dev web` starts the dev server
- `nx build web` produces a production build
- `nx test web` runs tests (initially empty)

---

### Step 3.2: Scaffold `packages/ui/`

**What:** Create the accessible component library using shadcn/ui + React Aria.

**Files to create:**
```
packages/ui/
├── package.json
├── project.json
├── tsconfig.json
├── src/
│   ├── index.ts
│   ├── components/
│   │   ├── button.tsx
│   │   ├── input.tsx
│   │   ├── dialog.tsx
│   │   ├── select.tsx (React Aria)
│   │   └── combobox.tsx (React Aria)
│   ├── hooks/
│   ├── lib/
│   │   └── utils.ts
│   └── styles/
│       └── globals.css
├── tests/
└── .storybook/
    ├── main.ts
    └── preview.ts
```

**packages/ui/package.json:**
```json
{
  "name": "@odysseus/ui",
  "version": "2.0.0",
  "private": true,
  "type": "module",
  "main": "./src/index.ts",
  "types": "./src/index.ts",
  "exports": {
    ".": "./src/index.ts",
    "./globals.css": "./src/styles/globals.css"
  },
  "scripts": {
    "test": "vitest run",
    "test:watch": "vitest",
    "storybook": "storybook dev -p 6007",
    "build-storybook": "storybook build",
    "lint": "eslint .",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "@radix-ui/react-dialog": "^1.1.2",
    "@radix-ui/react-dropdown-menu": "^2.1.2",
    "@radix-ui/react-tabs": "^1.1.2",
    "react-aria-components": "^1.5.0",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.1.1",
    "tailwind-merge": "^2.5.4"
  },
  "devDependencies": {
    "vitest": "^2.1.5",
    "@testing-library/react": "^16.0.1",
    "vitest-axe": "^0.1.0",
    "@storybook/react-vite": "^8.4.4",
    "@storybook/addon-a11y": "^8.4.4",
    "eslint": "^9.14.0",
    "typescript": "^5.6.0"
  }
}
```

**Commands:**
```bash
cd packages/ui
npm install
npm run storybook
npm test

git add packages/ui/
git commit -m "feat(ui): scaffold accessible component library"
```

**Dependencies:** Step 0.3 (shared config)  
**Risk:** Low (additive)  
**Validation:**
- `nx storybook ui` starts Storybook
- `nx test ui` runs component tests
- All components pass axe audits

---

### Step 3.3: Wire TanStack Query to the SDK

**What:** Create React Query hooks that wrap the generated SDK.

**Files to create:**
```
apps/web/src/hooks/
├── use-auth.ts
├── use-chat.ts
├── use-documents.ts
└── ... (one per domain)
```

**Example: `apps/web/src/hooks/use-auth.ts`:**
```typescript
import { useQuery, useMutation } from '@tanstack/react-query';
import { client } from '@odysseus/client-sdk';

export function useCurrentUser() {
  return useQuery({
    queryKey: ['auth', 'me'],
    queryFn: () => client.GET('/api/auth/me').then((res) => res.data),
  });
}

export function useLogin() {
  return useMutation({
    mutationFn: (credentials: { username: string; password: string }) =>
      client.POST('/api/auth/login', { body: credentials }).then((res) => res.data),
  });
}

export function useLogout() {
  return useMutation({
    mutationFn: () => client.POST('/api/auth/logout').then((res) => res.data),
  });
}
```

**Commands:**
```bash
cd apps/web
npm test

git add src/hooks/
git commit -m "feat(web): wire TanStack Query to the SDK"
```

**Dependencies:** Step 3.1, Step 1.2  
**Risk:** Low (additive)  
**Validation:**
- Hooks fetch data from the API
- React Query caching works
- Tests pass

---

### Phase 3 Git Strategy

**Branch:** `feat/phase-3-frontend`  
**Commits:**
```
feat(web): scaffold React 19 + Vite SPA
feat(ui): scaffold accessible component library
feat(web): wire TanStack Query to the SDK
feat(web): add light/dark theme support
feat(web): add Gherkin scenarios for core UI
test(web): add component tests and E2E tests
chore: enforce Lighthouse + axe budgets in CI
```

**PRs:** Multiple small PRs (one per step)  
**Review focus:**
- Accessibility (axe = 0 violations)
- Performance (Lighthouse perf budget met)
- Coverage ≥ 80%
- No hand-rolled accessible widgets

---

### Phase 3 Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Accessibility regressions | Medium | High | Enforce axe = 0 in CI; review all interactive components |
| Performance budget exceeded | Medium | Medium | Code-splitting; lazy loading; profile with Lighthouse |
| SDK types are wrong | Low | High | Regenerate SDK after each backend change; snapshot tests |
| Component library grows too large | Low | Low | Keep components focused; use shadcn/ui as starting point |

---

## Phase 4: Feature Migration (Weeks 23-40)

### Objective
Migrate features from the legacy vanilla-JS frontend to the React SPA, one domain at a time. Each slice: shared `.feature` → Playwright E2E → React screens on `packages/ui` → consume SDK. Delete each legacy `static/js` module when its features pass.

### Exit Criteria
- [ ] All core domains migrated (chat, documents, email, cookbook, notes/calendar, gallery, settings)
- [ ] Legacy `static/js` modules deleted as each domain is migrated
- [ ] Each migrated domain: 100% line+branch coverage, mutation ≥ threshold, axe 0, Lighthouse budget met
- [ ] SSE streaming works via SDK helpers
- [ ] No dual-ownership (each feature lives in either legacy or new, not both)

---

### Step 4.1: Migrate Auth Domain (Pilot)

**What:** Migrate the auth/login flow as a pilot slice.

**Files to create:**
```
apps/web/src/routes/login.tsx
apps/web/src/routes/register.tsx
features/auth-ui.feature
e2e/steps/auth-ui.steps.ts
```

**features/auth-ui.feature:**
```gherkin
@e2e @smoke @a11y
Feature: User authentication UI
  As a user
  I want to log in through the web interface
  So that I can access my workspace

  Scenario: Successful login
    Given I am on the login page
    When I enter my username "alice"
    And I enter my password "secret123"
    And I click the "Log in" button
    Then I am redirected to the home page
    And I see a welcome message "Welcome, alice"

  Scenario: Failed login (wrong password)
    Given I am on the login page
    When I enter my username "alice"
    And I enter my password "wrongpw"
    And I click the "Log in" button
    Then I see an error message "Invalid credentials"
    And I remain on the login page

  Scenario: Keyboard navigation
    Given I am on the login page
    When I press Tab
    Then the username field is focused
    When I press Tab again
    Then the password field is focused
    When I press Tab again
    Then the "Log in" button is focused
```

**e2e/steps/auth-ui.steps.ts:**
```typescript
import { Given, When, Then } from '@cucumber/cucumber';
import { expect } from '@playwright/test';
import { AxeBuilder } from '@axe-core/playwright';

Given('I am on the login page', async function () {
  await this.page.goto('/login');
});

When('I enter my username {string}', async function (username: string) {
  await this.page.getByLabel('Username').fill(username);
});

When('I enter my password {string}', async function (password: string) {
  await this.page.getByLabel('Password').fill(password);
});

When('I click the {string} button', async function (buttonText: string) {
  await this.page.getByRole('button', { name: buttonText }).click();
});

Then('I am redirected to the home page', async function () {
  await expect(this.page).toHaveURL('/');
});

Then('I see a welcome message {string}', async function (message: string) {
  await expect(this.page.getByText(message)).toBeVisible();
});

Then('I see an error message {string}', async function (message: string) {
  await expect(this.page.getByText(message)).toBeVisible();
});

Then('the {string} field is focused', async function (fieldName: string) {
  const field = this.page.getByLabel(fieldName);
  await expect(field).toBeFocused();
});

Then('the page passes axe accessibility audit', async function () {
  const results = await new AxeBuilder({ page: this.page }).analyze();
  expect(results.violations).toEqual([]);
});
```

**Commands:**
```bash
cd e2e
npx playwright test auth-ui

git rm static/js/login.js

git commit -m "feat(web): migrate auth domain to React SPA"
```

**Dependencies:** Phase 3  
**Risk:** Medium (pilot slice, low impact if it fails)  
**Validation:**
- E2E tests pass
- Accessibility audit passes
- Legacy auth UI deleted

---

### Step 4.2: Migrate Chat Domain

**What:** Migrate the chat interface (the core feature).

**Files to create:**
```
apps/web/src/routes/chat.tsx
apps/web/src/routes/chat.$sessionId.tsx
apps/web/src/components/chat/
├── message-list.tsx
├── message-input.tsx
├── session-sidebar.tsx
└── sse-handler.ts (streaming)
features/chat-ui.feature
e2e/steps/chat-ui.steps.ts
```

**Approach:**
1. Implement session list (sidebar)
2. Implement message list
3. Implement message input (with file upload)
4. Implement SSE streaming (via SDK helpers)
5. Implement tool-call rendering
6. Write E2E tests for core journeys
7. Delete legacy `static/js/chat.js`

**Dependencies:** Step 4.1  
**Risk:** High (chat is the core feature; any bug breaks the app)  
**Mitigation:**
- Migrate incrementally (session list → message list → input → streaming)
- Keep legacy chat working until new chat passes all tests
- Use feature flags to toggle between legacy and new chat

**Validation:**
- E2E tests pass
- SSE streaming works
- Accessibility audit passes
- Performance budget met (Lighthouse)

---

### Step 4.3: Migrate Remaining Domains

**What:** Migrate documents, email, cookbook, notes/calendar, gallery, settings.

**Approach:**
- Follow the same pattern as auth and chat
- Prioritize by user impact (documents > email > notes > calendar > gallery > cookbook > settings)
- Each domain: `.feature` → E2E → React screens → delete legacy

**Dependencies:** Step 4.2  
**Risk:** Medium (each domain has its own complexities)  
**Mitigation:**
- Keep slices small and vertical
- Never let legacy and new front ends both own a feature at once

**Validation:**
- Each domain: 100% line+branch coverage, mutation ≥ threshold, axe 0, Lighthouse budget met

---

### Phase 4 Git Strategy

**Branch:** `feat/phase-4-migration`  
**Commits (per domain):**
```
feat(web): migrate <domain> domain to React SPA
test(e2e): add E2E tests for <domain>
refactor: delete legacy <domain> UI
```

**PRs:** One PR per domain  
**Review focus:**
- Feature parity with legacy
- Accessibility and performance
- Coverage ≥ 100%

---

### Phase 4 Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Feature parity gaps | High | High | Write Gherkin scenarios before migrating; review with users |
| SSE streaming breaks | Medium | High | Test thoroughly; keep legacy streaming as fallback |
| Performance regressions | Medium | Medium | Profile with Lighthouse; optimize hot paths |
| Dual-ownership confusion | Medium | Low | Delete legacy UI as soon as new UI passes tests |

---

## Phase 5: Harden, Observe, Cut Over (Weeks 41-44)

### Objective
Full OTel observability, manual WCAG 2.2 AA audit, Lighthouse 100 on core routes, delete remaining dead code, remove test deps from runtime `requirements.txt`, publish docs site.

### Exit Criteria
- [ ] Full OTel (FE web-vitals RUM + BE traces) + dashboards
- [ ] Self-hosted error tracking (GlitchTip/Sentry)
- [ ] Manual WCAG 2.2 AA audit (NVDA/VoiceOver) signed off
- [ ] Lighthouse 100 on core routes
- [ ] Repo-wide mutation run passes
- [ ] Dead code deleted (`knip`/`vulture` clean)
- [ ] Test deps removed from runtime `requirements.txt`
- [ ] Docs site published
- [ ] v2.0 tagged and released

---

### Step 5.1: Full OTel Observability

**What:** Add frontend web-vitals RUM and backend traces; set up dashboards.

**Files to modify:**
```
apps/web/src/lib/otel.ts (new)
apps/web/src/main.tsx (initialize OTel)
apps/api/app.py (already has OTel from Phase 0)
```

**Commands:**
```bash
cd apps/web
npm test

OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318 nx dev web

git commit -m "feat(web): add frontend OTel observability"
```

**Dependencies:** Phase 4  
**Risk:** Low (additive)  
**Validation:**
- Traces appear in Grafana/Tempo
- Web-vitals metrics visible in dashboards

---

### Step 5.2: Manual WCAG 2.2 AA Audit

**What:** Perform a manual accessibility audit using NVDA and VoiceOver.

**Files to create:**
```
docs/accessibility-audit.md
```

**docs/accessibility-audit.md:**
```markdown
# Accessibility Audit (WCAG 2.2 AA)

**Date:** 2025-XX-XX  
**Auditor:** Jesse Glacken  
**Tools:** NVDA 2024.1, VoiceOver (macOS 14), axe-core 4.10

## Routes Tested
- [ ] / (home)
- [ ] /chat
- [ ] /chat/:sessionId
- [ ] /documents
- [ ] /settings

## Findings
| Route | Issue | Severity | Status |
|-------|--------|----------|--------|
| /chat | Missing ARIA label for message input | High | Fixed |
| /documents | Focus trap in modal dialog | Medium | Fixed |

## Sign-off
- [x] All critical issues resolved
- [x] All high-priority issues resolved
- [x] Keyboard navigation works on all routes
- [x] Screen reader announces all interactive elements
```

**Dependencies:** Phase 4  
**Risk:** Medium (manual audit can uncover issues)  
**Mitigation:**
- Allocate time for fixes
- Prioritize critical and high-severity issues

**Validation:**
- Audit document signed off
- All critical issues resolved

---

### Step 5.3: Delete Dead Code

**What:** Run `knip` (TypeScript) and `vulture` (Python) to find and delete dead code.

**Commands:**
```bash
cd apps/web
npx knip

git add -A
git commit -m "chore: delete dead code (knip)"

cd apps/api
uv run vulture . --min-confidence 80

git add -A
git commit -m "chore: delete dead code (vulture)"
```

**Dependencies:** Phase 4  
**Risk:** Medium (deleting code that might be needed)  
**Mitigation:**
- Review each deletion carefully
- Confirm no black-box scenario should reach the code
- If in doubt, keep the code and add a test

**Validation:**
- `knip` reports no dead code
- `vulture` reports no dead code
- All tests still pass

---

### Step 5.4: Publish Docs Site

**What:** Publish a documentation site using Docusaurus or MkDocs Material.

**Files to create:**
```
docs/site/
├── docusaurus.config.js
├── package.json
├── docs/
│   ├── intro.md
│   ├── setup.md
│   ├── architecture.md
│   ├── adr/
│   └── ... (other docs)
└── static/
    └── ... (images, etc.)
```

**Commands:**
```bash
cd docs/site
npm install
npm run build
npm run deploy

git add docs/site/
git commit -m "docs: publish documentation site"
```

**Dependencies:** Phase 4  
**Risk:** Low (documentation only)  
**Validation:**
- Docs site is live
- All ADRs are published
- Setup guide is complete

---

### Step 5.5: Tag v2.0 Release

**What:** Tag the v2.0 release and publish release notes.

**Commands:**
```bash
git tag -a v2.0.0 -m "Odysseus v2.0: Nx monorepo, contract-first API, React SPA"
git push origin v2.0.0

# Create GitHub release with release notes
```

**Dependencies:** Steps 5.1-5.4  
**Risk:** Low (tagging only)  
**Validation:**
- v2.0 tag exists
- GitHub release published
- Release notes are complete

---

### Phase 5 Git Strategy

**Branch:** `feat/phase-5-harden`  
**Commits:**
```
feat(web): add frontend OTel observability
docs: perform manual WCAG 2.2 AA audit
chore: delete dead code (knip/vulture)
docs: publish documentation site
chore: tag v2.0 release
```

**PR:** `feat/phase-5-harden` → `main`  
**Review focus:**
- Observability is complete
- Accessibility audit is signed off
- Dead code is deleted
- Docs site is live

---

### Phase 5 Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Manual audit uncovers critical issues | Medium | High | Allocate time for fixes; prioritize critical issues |
| Dead code deletion breaks something | Medium | High | Review carefully; keep code if in doubt |
| Docs site is incomplete | Low | Low | Use a checklist; review with team |
| v2.0 release is delayed | Medium | Medium | Keep phases small; ship incrementally |

---

## CI Pipeline Shape

### Pre-commit (fast, staged files only)
- File hygiene (trailing whitespace, EOF, YAML/JSON/TOML validation)
- Secret detection (gitleaks)
- Python linting (ruff, advisory until Phase 2)
- Coverage pragma ban (advisory until Phase 1)
- Type-ignore ban (advisory until Phase 2)
- Runtime deps guard (blocking after Phase 0.5)
- Response model checker (blocking per domain after Phase 1)

### Pre-push (heavier, whole-project)
- Full mypy --strict (advisory until Phase 2)
- Full tsc --noEmit (advisory until Phase 3)
- Coverage on affected (advisory until Phase 1)
- Dead code scan (vulture/knip, advisory until Phase 2)

### CI (GitHub Actions)
- Python syntax check (compileall)
- JS syntax check (node --check for legacy, tsc for new)
- Python tests (pytest)
- Quality gates (advisory until Phase 1)
- Mutation testing (mutmut/Stryker, CI-only)
- Lighthouse CI (axe + perf budgets, CI-only)
- E2E tests (Playwright + playwright-bdd)
- OpenAPI schema snapshot test
- SDK regeneration drift test

### Release
- Manual WCAG audit (NVDA/VoiceOver)
- Full mutation run
- Docs site deployment
- GitHub release

---

## Testing Strategy Summary

### Phase 0
- Existing test suite still runs (4,678 tests)
- Advisory gates produce reports
- No new tests required

### Phase 1
- Gherkin .feature files for each domain
- Black-box API tests (pytest-bdd)
- Coverage ≥ 90% per domain
- Mutation testing (mutmut) per domain

### Phase 2
- Refactored code maintains coverage
- Black-box tests still pass
- No new internal mocks
- Mutation testing (mutmut) for refactored modules

### Phase 3
- Component tests (Vitest + Testing Library)
- Accessibility tests (vitest-axe)
- Storybook stories with a11y addon
- Coverage ≥ 80%

### Phase 4
- E2E tests (Playwright + playwright-bdd)
- Accessibility tests (axe-core/playwright)
- Performance tests (Lighthouse CI)
- Coverage ≥ 100% per domain

### Phase 5
- Repo-wide mutation run
- Manual WCAG audit
- Dead code scan (knip/vulture)
- Full test suite green

---

## Dependency Graph

```
Phase 0 (Foundation)
  └─> Phase 1 (Contract-First)
        └─> Phase 2 (Decoupling)
              └─> Phase 3 (Frontend Foundation)
                    └─> Phase 4 (Feature Migration)
                          └─> Phase 5 (Harden & Release)
```

**Parallel work:**
- Phase 1 and Phase 2 can overlap once auth domain is clean
- Phase 3 can start once client-sdk is generated (Phase 1)
- Phase 4 can start once apps/web and packages/ui are scaffolded (Phase 3)

---

## Risk Register

| Phase | Risk | Likelihood | Impact | Mitigation |
|-------|------|-----------|--------|------------|
| 0 | File moves break imports | Medium | High | Run full test suite; fix import errors |
| 0 | Advisory gates too noisy | Medium | Low | Tune thresholds; keep continue-on-error |
| 1 | Response models are wrong | High | Medium | Review with team; use request_models.py |
| 1 | Coverage stalls at 70% | Medium | High | Focus on routes layer; delete dead code |
| 1 | Mutation testing reveals weak tests | High | Medium | Add stronger assertions |
| 2 | stream_agent_loop decomposition bugs | High | High | Extract one submodule at a time; test thoroughly |
| 2 | src/ regrouping breaks imports | High | Medium | Use re-export shims; update incrementally |
| 2 | Repository layer adds latency | Low | Medium | Profile; optimize hot paths |
| 2 | database.py split causes errors | Medium | High | Use re-exports; update importers gradually |
| 3 | Accessibility regressions | Medium | High | Enforce axe = 0 in CI |
| 3 | Performance budget exceeded | Medium | Medium | Code-splitting; lazy loading |
| 3 | SDK types are wrong | Low | High | Regenerate SDK; snapshot tests |
| 4 | Feature parity gaps | High | High | Write Gherkin scenarios first |
| 4 | SSE streaming breaks | Medium | High | Test thoroughly; keep legacy as fallback |
| 4 | Performance regressions | Medium | Medium | Profile with Lighthouse |
| 5 | Manual audit uncovers issues | Medium | High | Allocate time for fixes |
| 5 | Dead code deletion breaks something | Medium | High | Review carefully; keep if in doubt |

---

## Tooling Versions Summary

### Python
- Python: 3.11+
- FastAPI: ≥0.115.0
- Pydantic: ≥2.13.4
- SQLAlchemy: ≥2.0.36
- pytest: ≥8.3.4
- pytest-asyncio: ≥0.24.0
- pytest-cov: ≥5.0.0
- ruff: ≥0.7.0
- mypy: ≥1.13.0
- radon: ≥3.3.2
- mutmut: ≥2.5.0
- vulture: ≥2.11
- pre-commit: ≥4.0.1
- uv: latest

### TypeScript/Node
- Node: 20+
- TypeScript: ≥5.6.0
- React: ≥19.0.0
- Vite: ≥6.0.0
- Vitest: ≥2.1.5
- @testing-library/react: ≥16.0.1
- vitest-axe: ≥0.1.0
- axe-core: ≥4.10.2
- Storybook: ≥8.4.4
- ESLint: ≥9.14.0
- typescript-eslint: ≥8.15.0
- eslint-plugin-jsx-a11y: ≥6.10.2
- Tailwind: ≥3.4.15
- @tanstack/react-query: ≥5.62.0
- @tanstack/react-router: ≥1.92.0
- openapi-typescript: ≥7.4.3
- openapi-fetch: ≥0.1.0
- Playwright: latest
- playwright-bdd: latest

### Nx
- nx: ≥20.3.0
- @nx/js: ≥20.3.0
- @nxlv/python: ≥18.0.0

### Accessibility
- @radix-ui/react-dialog: ≥1.1.2
- @radix-ui/react-dropdown-menu: ≥2.1.2
- @radix-ui/react-tabs: ≥1.1.2
- react-aria-components: ≥1.5.0
- shadcn/ui: latest (via CLI)

### Observability
- opentelemetry-api: ≥1.28.0
- opentelemetry-sdk: ≥1.28.0
- opentelemetry-instrumentation-fastapi: ≥0.49b0
- opentelemetry-exporter-otlp-proto-http: ≥1.28.0
- @opentelemetry/web-sdk: latest

---

## Final Notes

This plan is a living document. As the migration progresses, update it with:
- Actual durations (vs. estimates)
- Lessons learned
- Risks that materialized and how they were handled
- Changes to the target structure or tooling

The key to success is:
1. **Strangler migration**: Keep the legacy app running until the replacement passes all gates
2. **Small, vertical slices**: Migrate one domain at a time; never let legacy and new both own a feature
3. **Advisory-first gates**: Start with report-only gates; flip to blocking per domain as each goes green
4. **Black-box testing**: Test through public surfaces; no internal mocking
5. **Accessibility as a gate**: Enforce axe = 0 and Lighthouse a11y = 100 from day one

Good luck with the migration!
