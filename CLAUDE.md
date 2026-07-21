# CLAUDE.md — Claude Code

**Read [`AGENTS.md`](AGENTS.md) and the relevant record in [`docs/adr/`](docs/adr/) before
writing code.** `AGENTS.md` is the canonical engineering brief for this repo; the ADRs are the
binding source of truth. This file only summarises; on any conflict, the ADRs win.

Odysseus is **mid-migration** to a v2 Nx monorepo (contract-first FastAPI + React/shadcn).
All new/modified code follows v2 standards. Don't extend the legacy `static/js/*` front end;
new UI goes in `apps/web` on `packages/ui`.

## Non-negotiables (full list in AGENTS.md)

1. **Contract-first** (ADR-0001): typed `response_model` on every endpoint; the FE calls the API
   only through the **generated** `packages/client-sdk` — no raw `fetch()`; never hand-edit the SDK.
2. **Layering** (ADR-0001/0002): domain code never imports `routes/`; FE↔BE only via the SDK;
   `packages/*` never import `apps/*`; use the Nx task graph.
3. **Black-box tests only** (ADR-0004): test HTTP endpoints and the DOM by role/name; never test
   privates or mock internal collaborators to hit coverage.
4. **Gherkin** (ADR-0004): behaviour in `features/*.feature`, driving `pytest-bdd`/`playwright-bdd`.
5. **100% line+branch** (ADR-0004): never lower thresholds or add `# pragma: no cover` /
   `c8 ignore` / `istanbul ignore` to dodge the gate.
6. **Mutation testing** (ADR-0004): fix surviving mutants with real assertions, not annotations.
7. **Dead code is deleted** (ADR-0004), after confirming no black-box scenario should reach it.
8. **Accessibility is absolute** (ADR-0005): WCAG 2.2 AA, `axe` 0 violations, Lighthouse a11y 100;
   use `packages/ui` (Radix/React Aria) primitives — never hand-roll accessible widgets; i18n all
   user-facing strings.
9. **Performance budgeted** (ADR-0005); **strict types** (`mypy --strict`, `tsc`) with no `any` /
   `type: ignore` escapes; **SOLID**, no new God modules; keep the security CI green.
10. **Honor ADRs**: significant decision → add/update an ADR (`docs/adr/0000-template.md`); never
    silently contradict an Accepted one.

**Done** = black-box tests green · 100% line+branch · mutation ≥ threshold · axe 0 / Lighthouse
a11y 100 · perf budget met · OpenAPI snapshot ok + SDK regenerated · mypy/ruff/tsc/ESLint clean ·
knip/vulture clean. Prefer `nx affected -t lint test typecheck e2e`.
