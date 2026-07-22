# Task for planner

You are a delegated subagent running from a fork of the parent session. Treat the inherited conversation as reference-only context, not a live thread to continue. Do not continue or answer prior messages as if they are waiting for a reply. Your sole job is to execute the task below and return a focused result for that task using your tools.

Task:
You are assessing whether the existing Linear backend tickets (ODY-6 through ODY-24, which cover Phase 0 foundation + Phase 1 contract-first + Phase 2 backend decoupling) are sufficient to produce a backend that:
1. Maps ALL 483 endpoints to an OpenAPI contract (currently only 3 of 483 have `response_model`)
2. Maintains all existing functionality (tests pass, behaviors preserved)
3. Raises coverage to 100% line+branch from current 47.5%
4. Makes tests MEANINGFUL (currently 3,984 mocks/patches vs 366 HTTP-level tests — heavily mock-dependent, violating ADR-0004 black-box mandate)
5. Functions as a drop-in replacement for the existing frontend (876 raw fetch() calls)
6. Is a rock-solid foundation for the new React SPA

Below is the full backend analysis data. Compare against the existing tickets and identify gaps.

## Existing Backend Structure (v1)

### Routes (43,766 LOC, 67 files, 6 subpackages)
```
483 endpoints: 217 POST, 192 GET, 41 DELETE, 23 PUT, 10 PATCH
Only 3 have response_model (chat_routes.py, memory/memory_routes.py, session_routes.py)

Largest route files:
  email_routes.py:    5,226 LOC, 54 endpoints (largest — IMAP/SMTP, compose, threading)
  cookbook_routes.py: 4,386 LOC, 17 endpoints (model download/serve)
  model_routes.py:    2,657 LOC, 19 endpoints
  gallery/:           1,966 LOC, 32 endpoints
  document_routes.py: 1,810 LOC, 23 endpoints
  shell_routes.py:    1,778 LOC, 6 endpoints
  chat_routes.py:     1,777 LOC, 8 endpoints (includes SSE streaming — critical)
  calendar_routes.py: 1,667 LOC, 19 endpoints (CalDAV sync)
  skills_routes.py:   1,662 LOC, 21 endpoints
  session_routes.py:  1,321 LOC, 19 endpoints
  auth_routes.py:      836 LOC, 29 endpoints
  ... 50+ more files
```

### Domain Layer — src/ (46,673 LOC, 139 files, flat)
```
God modules:
  agent_loop.py:      4,529 LOC (stream_agent_loop CC=531)
  llm_core.py:        2,869 LOC (_stream_llm_inner CC=216)
  builtin_actions.py: 2,776 LOC (13 of the 36 backward imports)
  task_scheduler.py:  2,627 LOC
  core/database.py:   2,562 LOC (56-file fan-in, 28 models)
```

### Backward Imports
```
36 src→routes imports across 13 src/ files
  src/builtin_actions.py:      ~13 (heaviest — imports email_helpers, skills_routes, note_routes, prefs_routes)
  src/caldav_sync.py:           3
  src/agent_loop.py:            2
  src/interactive_gate.py:      1
  src/ai_interaction.py:        1
  ... (all are inline function-body imports to dodge circular imports)
```

### Test Suite (81,577 LOC, 734 files, 3,248 test functions)
```
Current coverage: 47.5% lines overall (routes 36%)
  core/    72.6%
  services/ 64.1%
  src/     54.9%
  routes/  35.6%
  app.py   0.4%

Test quality issues:
  3,984 mock.patch/unittest.mock calls — heavily mock-dependent
  366 HTTP TestClient/httpx calls — thin integration waist
  No tests/bdd/ directory — NO Gherkin .feature files
  Tests import stubs that replace core.database, sqlalchemy, etc. at MODULE SCOPE

Infrastructure issues:
  pytest, pytest-asyncio, httpx2 still in runtime requirements.txt (not dev deps)
  4 `# pragma: no cover` exclusions
  22 `# type: ignore` exclusions
  No flake8/ruff/mypy in CI (ruff okay in pre-commit)
```

### Existing Backend Tickets:
- P0.1 (ODY-7): Initialize Nx Workspace
- P0.2 (ODY-6): Relocate Backend into apps/api/
- P0.3 (ODY-8): Create packages/config/
- P0.4 (ODY-10): Scaffold Advisory CI Gates
- P0.5 (ODY-11): Remove Test Deps from Runtime
- P0.7 (ODY-9): Integrate OTel Skeleton
- P1.1 (ODY-12): Create packages/contracts/ (OpenAPI schema)
- P1.2 (ODY-17): Create packages/client-sdk/ (TS client)
- P1.3a (ODY-16): Typed Response Models — Auth Domain
- P1.3b (ODY-13): Typed Response Models — Chat Domain
- P1.3c (ODY-15): Typed Response Models — Documents Domain
- P1.3d (ODY-14): Typed Response Models — Email Domain
- P1.3e (ODY-23): Typed Response Models — Remaining Domains
- P1.4 (ODY-24): Flip Quality Gates to Blocking
- P2.1 (ODY-18): Decompose stream_agent_loop
- P2.2 (ODY-19): Regroup src/ into Domain Packages
- P2.3 (ODY-20): Introduce Repository Layer
- P2.4 (ODY-22): Remove src→routes Backward Imports
- P2.5 (ODY-21): Split core/database.py

## Task
Identify gaps in the backend ticket coverage. For each gap:
1. Is it a new ticket, or does an existing ticket need scope expansion?
2. What are the concrete details?
3. What are the dependencies and priority?

---
**Output:**
Write your findings to exactly this path: /home/jesse/git/odysseus-jg/.pi-subagents/artifacts/outputs/3bc9eeb4/plan.md
This path is authoritative for this run.
Ignore any other output filename or output path mentioned elsewhere, including output destinations in the base agent prompt, system prompt, or task instructions.

## Acceptance Contract
Acceptance level: checked
Completion is not accepted from prose alone. End with a structured acceptance report.

Criteria:
- criterion-1: Implement the requested change without widening scope

Required evidence: changed-files, tests-added, commands-run, residual-risks, no-staged-files

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