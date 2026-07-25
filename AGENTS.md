# AGENTS.md — Engineering standards for coding agents

**This file is the canonical brief for every AI coding assistant working in this repo**
(Claude Code, Gemini CLI, OpenAI Codex, Cline, Cursor, GitHub Copilot, OpenCode, Pi,
Windsurf, Aider, Zed, and any other). Tool-specific files (`CLAUDE.md`, `GEMINI.md`,
`.github/copilot-instructions.md`, `.cursor/rules/`, `.clinerules/`, `.windsurfrules`) are
thin pointers to this document. **On any conflict, the [ADRs in `docs/adr/`](docs/adr/) win.**

Read this file and the relevant ADR **before** writing code. If a task appears to require
violating a rule below, stop and say so — do not work around it silently.

---

## Where the repo is right now

Odysseus is **mid-migration** from a v1 FastAPI + vanilla-JS monolith to the v2 structure in
the ADRs. Both may exist at once. **All new and modified code follows the v2 standards below.**
Do not add new work to the legacy vanilla-JS front end (`static/js/*`) except minimal fixes;
new UI belongs in `apps/web` on `packages/ui`.

### Branch policy
- The default branch on GitHub is `dev`. **All pull requests must target `dev2`**, not `dev` or `main`.
- Feature branches should be named `jesserglacken/<ticket>-<short-description>`.
- Convention: `git checkout dev2 && git pull origin dev2 && git checkout -b <branch>` before starting work.
- Phase 2 refactoring is complete. Phase 3 (frontend) and beyond target `dev2`.

---

## The non-negotiables

These are binding. Each traces to an ADR.

1. **Contract-first API.** (ADR-0001) The OpenAPI schema is the source of truth. Every
   endpoint declares a typed `response_model` + request models. Never hand-write or hand-edit
   the TypeScript client — it is **generated** into `packages/client-sdk` from the schema. The
   front end calls the backend **only** through that SDK; **no raw `fetch()` to API routes.**
2. **Respect the layering.** (ADR-0001/0002) FE↔BE couple only via `packages/client-sdk`.
   Backend domain/agent/LLM code must **not** import from `routes/`. Data access goes through
   the repository layer, not scattered `core.database` calls. `packages/*` never import from
   `apps/*`. Put code in the correct Nx project; don't bypass the task graph.
3. **Black-box tests only.** (ADR-0004) Test through public surfaces: HTTP endpoints on the
   backend; the DOM by **role / accessible name / label** on the front end. **Never** test
   private functions or implementation detail, and **never mock internal collaborators** to
   manufacture coverage. Only external boundaries (network, clock, filesystem) may be controlled.
4. **Describe behaviour in Gherkin.** (ADR-0004) Requirements live as `.feature` files in
   `features/` (Given/When/Then), driving `pytest-bdd` and `playwright-bdd`. Tests trace to
   product requirements.
5. **100% line AND branch coverage — do not dodge it.** (ADR-0004) Never lower thresholds and
   **never add coverage-exclusion pragmas** (`# pragma: no cover`, `/* c8 ignore */`,
   `istanbul ignore`) to pass the gate. Write the test.
6. **Mutation tests must pass.** (ADR-0004) When mutants survive, add real assertions — do not
   annotate them away.
7. **Dead code is deleted, not excused.** (ADR-0004) Code unreachable by the black-box suite is
   removed (`knip`/`vulture`) **after confirming** no black-box scenario *should* reach it. If
   one should, the missing test is the bug. Never comment out or ignore-annotate to satisfy it.
8. **Accessibility is absolute — WCAG 2.2 AA.** (ADR-0005) Every UI change keeps **`axe` = 0
   violations** and **Lighthouse a11y = 100**. Use semantic HTML and `packages/ui`
   (Radix/React Aria) primitives; **never hand-roll** dialogs, menus, comboboxes, tabs, etc.
   Keyboard + visible focus + reduced-motion + AA contrast in light **and** dark. No hard-coded
   user-facing strings — use the i18n layer.
9. **Performance is budgeted.** (ADR-0005) Respect Lighthouse per-route budgets (perf = 100 on
   core routes). Don't add heavy deps or block the main thread; prefer code-splitting/lazy load.
10. **Strict types, no escapes.** `mypy --strict` and `tsc` strict must stay clean. Avoid `any`
    and `# type: ignore` / `@ts-expect-error`; if truly unavoidable, justify it in a comment.
11. **SOLID & no new giants.** Small, single-responsibility units. Do not create new God modules
    or functions above the agreed cyclomatic-complexity budget; prefer extraction.
12. **Keep the existing security posture.** Never weaken the CI security suite (Trivy, gitleaks,
    zizmor, hadolint, pip-audit). No secrets in code. Keep test-only deps out of runtime
    `requirements.txt`.
13. **Honor the ADRs.** Making an architecturally significant decision? **Add or update an ADR**
    (`docs/adr/`, use `0000-template.md`). Never silently contradict an Accepted ADR — propose a
    superseding one instead.

## Definition of done (every change)

A change is done only when all apply: black-box tests added/updated and green; **100% line+branch**;
**mutation ≥ threshold**; **axe 0 / Lighthouse a11y 100**; perf budget met; OpenAPI snapshot
unchanged or intentionally updated + SDK regenerated; `mypy --strict`/`ruff`/`tsc`/ESLint clean;
`knip`/`vulture` clean; features trace to requirements. Run via the Nx graph
(`nx affected -t lint test typecheck e2e`).

## Enforcement model (why these stick)

Instruction files make the rules visible; **CI gates make them binding.** Prose can be ignored;
a red pipeline cannot. The gates above are the backstop. An agent that thinks a rule is wrong
proposes a superseding ADR — it does not quietly bypass the rule or the gate.

## Which file each tool reads

| Tool | Reads |
|------|-------|
| OpenAI Codex, OpenCode, Pi, Aider, Zed, Jules | `AGENTS.md` (this file) — native |
| Claude Code | `CLAUDE.md` → points here |
| Gemini CLI | `GEMINI.md` → points here |
| GitHub Copilot | `.github/copilot-instructions.md` → points here |
| Cursor | `.cursor/rules/engineering-standards.mdc` → points here |
| Cline | `.clinerules/engineering-standards.md` → points here |
| Windsurf | `.windsurfrules` → points here |
| Any other | Read this file and `docs/adr/`. |

See [`docs/adr/`](docs/adr/) for the full decisions and rationale.
