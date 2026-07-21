# GitHub Copilot instructions

**The canonical brief is [`AGENTS.md`](../AGENTS.md); the binding source of truth is
[`docs/adr/`](../docs/adr/). Read them before suggesting code.** On conflict, the ADRs win.

Odysseus is **mid-migration** to a v2 Nx monorepo (contract-first FastAPI + React/shadcn). New
and modified code follows v2 standards. Don't extend legacy `static/js/*`; new UI lives in
`apps/web` on `packages/ui`.

## Non-negotiables (full list in AGENTS.md)

1. **Contract-first** (ADR-0001): every endpoint has a typed `response_model`; the front end
   calls the API only through the **generated** `packages/client-sdk` — no raw `fetch()`; never
   hand-edit the SDK.
2. **Layering** (ADR-0001/0002): domain code never imports `routes/`; FE↔BE only via the SDK;
   `packages/*` never import `apps/*`; use the Nx task graph.
3. **Black-box tests only** (ADR-0004): test HTTP endpoints and the DOM by role/accessible name;
   never test private functions or mock internal collaborators to reach coverage.
4. **Gherkin** (ADR-0004): behaviour in `features/*.feature`, driving `pytest-bdd`/`playwright-bdd`.
5. **100% line+branch** (ADR-0004): do not lower thresholds or add coverage-exclusion pragmas
   (`# pragma: no cover`, `c8 ignore`, `istanbul ignore`).
6. **Mutation testing** (ADR-0004): fix surviving mutants with real assertions, not annotations.
7. **Dead code is deleted** (ADR-0004), after confirming no black-box scenario should reach it.
8. **Accessibility is absolute** (ADR-0005): WCAG 2.2 AA, `axe` 0 violations, Lighthouse a11y 100;
   use `packages/ui` (Radix/React Aria) primitives — never hand-roll accessible widgets; i18n all
   user-facing strings.
9. **Performance budgeted** (ADR-0005); **strict types** (`mypy --strict`, `tsc`) with no `any` /
   `type: ignore` escapes; **SOLID**, no new God modules; keep the security CI green.
10. **Honor ADRs**: an architecturally significant change adds/updates an ADR; never silently
    contradict an Accepted one.
