# Task for planner

You are a delegated subagent running from a fork of the parent session. Treat the inherited conversation as reference-only context, not a live thread to continue. Do not continue or answer prior messages as if they are waiting for a reply. Your sole job is to execute the task below and return a focused result for that task using your tools.

Task:
You are devising a phased, executable refactoring plan for the Odysseus project — a migration from a v1 FastAPI + vanilla-JS monolith to a v2 Nx polyglot monorepo with rigorous architectural standards.

## Background context from the docs

### Current state (v1 — what we have now)
- FastAPI monolith, single-process Uvicorn serving a static vanilla-JS frontend
- Flat structure: app.py (1,281 LOC), core/ (11 files, 4,855 LOC), routes/ (67 files, 43,699 LOC — 6 subpackaged), src/ (139 files, 53,814 LOC — flat, no domain grouping), services/ (40 files, 10,055 LOC), mcp_servers/ (5 files), integrations/ (2 files)
- God modules: src/agent_loop.py (4,529 LOC, stream_agent_loop CC=531), routes/email_routes.py (5,226 LOC), src/llm_core.py (2,869 LOC, _stream_llm_inner CC=216), core/database.py (2,562 LOC, 56-file fan-in)
- 36 backward src→routes imports
- Frontend: 153 vanilla ES modules, 133k LOC, zero tests, 40k-line style.css
- 465 endpoints, only 3 declare a response_model
- 876 raw fetch() calls from frontend to backend
- 4,678 Python tests at 47.5% overall coverage (routes 36%, frontend 0%)
- Strong security CI (Trivy, gitleaks, zizmor, hadolint, pip-audit)

### Target state (v2 — where we're going per the ADRs)
Nx polyglot monorepo with:
- apps/api/ — FastAPI backend (relocated from root, src-layout + pyproject build)
- apps/web/ — React 19 + TypeScript + Vite SPA
- packages/contracts/ — openapi.json (source of truth) + schema snapshot tests
- packages/client-sdk/ — generated typed TS client (replaces 876 raw fetch() calls)
- packages/ui/ — shadcn/ui on Radix + React Aria components + design tokens + Tailwind
- packages/config/ — shared ESLint/tsconfig/Tailwind/Vitest/ruff presets
- features/ — Gherkin .feature files (shared FE+BE product requirements)
- e2e/ — Playwright + playwright-bdd black-box tests
- tools/ — Nx generators, codegen, migration scripts
- docs/ — ADRs, C4 diagrams, docs site

### Five Accepted ADRs governing everything:
1. ADR-0001: Contract-first API — OpenAPI schema is source of truth, typed response_model on every endpoint, generated TS SDK, no raw fetch(), no src→routes imports
2. ADR-0002: Nx polyglot monorepo with strict boundaries (packages/* never import apps/*)
3. ADR-0003: React SPA on shadcn/ui + React Aria, TanStack Query + Router, Tailwind tokens
4. ADR-0004: Black-box tests only, Gherkin .feature files, 100% line+branch coverage, mutation testing must pass, dead code is deleted
5. ADR-0005: WCAG 2.2 AA non-negotiable (axe=0, Lighthouse a11y=100), performance budgeted per-route

### The ADR states that all gates start advisory and flip to blocking per-domain once clean.

### Migration roadmap phases (from docs/migration-roadmap.md):
- Phase 0 (Foundation & guardrails): Nx workspace, relocate backend into apps/api, CI scaffolding advisory-first
- Phase 1 (Contract-first backend): Typed response_models across 465 endpoints domain-by-domain, emit openapi.json, generate SDK, .feature files as black-box API tests
- Phase 2 (Backend decoupling & SOLID): Decompose stream_agent_loop, regroup flat src/, repository layer, remove 36 src→routes imports
- Phase 3 (Front-end foundation): Scaffold apps/web + packages/ui, wire SDK behind TanStack Query, Lighthouse + axe budgets
- Phase 4 (Feature migration vertical slices): One domain at a time, delete legacy static/js modules
- Phase 5 (Harden, observe, cut over): Full OTel, manual WCAG audit, delete remaining dead code, publish docs

## Your task

Produce a **detailed, phased, step-by-step implementation plan** that a coding agent can execute. For each phase, list:

1. **Concrete steps** — what files to create, move, or modify; what commands to run; what the exit criteria are
2. **Tooling choices** — exact Nx/TypeScript/Python package versions and configurations
3. **Dependencies between steps** — what must be done before what
4. **Git strategy** — branch naming, PR sequencing, commit conventions
5. **Risk areas** — what could break, how to mitigate
6. **Testing strategy per phase** — how to validate each step (consistent with black-box/Gherkin/100% coverage)

Be precise and actionable — this will be given to engineering agents to execute. Include the exact Nx project configuration (project.json, workspace layout, generators), the Python package structure (pyproject.toml with build-system, src-layout), and the CI pipeline shape.

Assume the engineer has access to the current tree at /home/jesse/git/odysseus-jg.

---
**Output:**
Write your findings to exactly this path: /home/jesse/git/odysseus-jg/.pi-subagents/artifacts/outputs/397a3adf/plan.md
This path is authoritative for this run.
Ignore any other output filename or output path mentioned elsewhere, including output destinations in the base agent prompt, system prompt, or task instructions.

## Acceptance Contract
Acceptance level: reviewed
Completion is not accepted from prose alone. End with a structured acceptance report.

Criteria:
- criterion-1: Implement the requested change without widening scope
- criterion-2: Return evidence sufficient for an independent acceptance review

Required evidence: changed-files, tests-added, commands-run, validation-output, residual-risks, no-staged-files

Review gate: required by reviewer.

Finish with a fenced JSON block tagged `acceptance-report` in this shape:
Use empty arrays when no items apply; array fields contain strings unless object entries are shown.
`criteriaSatisfied[].status` must be exactly one of: satisfied, not-satisfied, not-applicable.
`commandsRun[].result` must be exactly one of: passed, failed, not-run.
`manualNotes` and `notes` are optional strings; an empty string means no note and does not satisfy `manual-notes` evidence.
```acceptance-report
{
  "criteriaSatisfied": [
    {
      "id": "criterion-1",
      "status": "satisfied",
      "evidence": "specific proof"
    },
    {
      "id": "criterion-2",
      "status": "satisfied",
      "evidence": "specific proof"
    }
  ],
  "changedFiles": [
    "src/file.ts"
  ],
  "testsAddedOrUpdated": [
    "test/file.test.ts"
  ],
  "commandsRun": [
    {
      "command": "command",
      "result": "passed",
      "summary": "short result"
    }
  ],
  "validationOutput": [
    "validation output or concise summary"
  ],
  "residualRisks": [
    "none"
  ],
  "noStagedFiles": true,
  "diffSummary": "short description of the diff",
  "reviewFindings": [
    "blocker: file.ts:12 - issue found, or no blockers"
  ],
  "manualNotes": "anything else the parent should know"
}
```