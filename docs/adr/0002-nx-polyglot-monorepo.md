# ADR-0002: Adopt an Nx polyglot monorepo

- **Status:** Accepted
- **Date:** 2026-07-21
- **Deciders:** Repository owner
- **Supersedes:** none
- **Superseded by:** none

## Context

v2 decouples a Python back end (ADR-0001) from a React front end (ADR-0003) joined only by
a generated contract. That requires a repository that can build, test, and cache work across
**both Python and TypeScript**, run only what a change affects, and provide consistent
generators so new projects follow the standards by default. Turborepo is JS-only; Bazel is
polyglot but heavy. Nx supports a polyglot graph (TS first-class, Python via `@nxlv/python`)
with affected-only execution and remote caching.

## Decision

The repository is an **Nx workspace** with this structure:

```
apps/
  web/          # React 19 + Vite SPA (ADR-0003)
  api/          # FastAPI (ADR-0001); src-layout + pyproject build-system
packages/
  contracts/    # openapi.json (source of truth) + schema snapshot tests
  client-sdk/   # generated typed TS client
  ui/           # shadcn/ui (owned) on Radix + React Aria + design tokens
  config/       # shared eslint / tsconfig / tailwind / vitest / ruff presets
features/       # Gherkin .feature files (product requirements; shared FE+BE)
e2e/            # Playwright + playwright-bdd (black-box)
tools/          # Nx generators, codegen, migration scripts
docs/           # ADRs, C4 diagrams, docs site
```

Rules:
- **Every unit of code lives in the correct Nx project.** Do not add loose top-level
  modules or cross-project relative imports that bypass project boundaries.
- **Use the Nx task graph** (`nx build`, `nx test`, `nx affected`) — do not invent parallel
  ad-hoc build scripts. CI runs `nx affected`.
- **Dependencies flow inward only:** `apps/*` depend on `packages/*`; `packages/*` do not
  depend on `apps/*`. `apps/web` reaches the API only via `packages/client-sdk`.
- **The Python API is a proper installable package** (`pyproject.toml` with a build-system),
  not a script rooted at `BASE_DIR`.

Migration is **strangler-style**: the legacy monolith keeps running while projects are moved
in; nothing is deleted until its replacement passes the gates.

## Consequences

- **Positive:** one place to enforce standards; fast CI via affected+cache; clear ownership
  and dependency boundaries; generators bake the rules into new code.
- **Negative / costs:** Nx has a learning curve; the polyglot Python integration relies on a
  community plugin that must be kept current.
- **Enforcement:** Nx module-boundary lint rules (`@nx/enforce-module-boundaries`); CI runs
  through Nx; project generators are the sanctioned way to scaffold.

## Alternatives considered

- **Turborepo + pnpm workspaces.** Rejected: JS/TS-first; the Python API would sit outside
  the managed graph.
- **Bazel.** Rejected: hermetic and powerful but disproportionate setup/maintenance cost for
  this team size.
- **Multi-repo.** Rejected: splits the contract, the shared Gherkin, and the gates across
  repos, weakening exactly the coupling discipline v2 is built around.
