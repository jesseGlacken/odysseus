# GEMINI.md — Gemini CLI

**Read [`AGENTS.md`](AGENTS.md) and the relevant [`docs/adr/`](docs/adr/) record before writing
code.** `AGENTS.md` is the canonical brief; the ADRs are the binding source of truth. This file
summarises only — on conflict, the ADRs win.

Odysseus is **mid-migration** to a v2 Nx monorepo (contract-first FastAPI + React/shadcn). All
new/modified code follows v2 standards; don't extend legacy `static/js/*` — new UI lives in
`apps/web` on `packages/ui`.

## Non-negotiables (full list in AGENTS.md)

1. **Contract-first** (ADR-0001): typed `response_model` per endpoint; FE calls the API only via
   the **generated** `packages/client-sdk` — no raw `fetch()`; never hand-edit the SDK.
2. **Layering** (ADR-0001/0002): domain code never imports `routes/`; FE↔BE only via the SDK;
   `packages/*` never import `apps/*`; use the Nx task graph.
3. **Black-box tests only** (ADR-0004): HTTP endpoints + DOM by role/name; never test privates or
   mock internal collaborators for coverage.
4. **Gherkin** (ADR-0004): `features/*.feature` drive `pytest-bdd`/`playwright-bdd`.
5. **100% line+branch** (ADR-0004): never lower thresholds or add `# pragma: no cover` /
   `c8 ignore` / `istanbul ignore`.
6. **Mutation testing** (ADR-0004): fix surviving mutants with real assertions.
7. **Dead code is deleted** (ADR-0004) after confirming no black-box scenario should reach it.
8. **Accessibility is absolute** (ADR-0005): WCAG 2.2 AA, `axe` 0, Lighthouse a11y 100; use
   `packages/ui` (Radix/React Aria) primitives — never hand-roll; i18n all strings.
9. **Perf budgeted** (ADR-0005); **strict types** (no `any` / `type: ignore` escapes); **SOLID**,
   no new God modules; keep the security CI green.
10. **Honor ADRs**: significant decision → add/update an ADR; never silently contradict one.

**Done** = black-box tests green · 100% line+branch · mutation ≥ threshold · axe 0 / Lighthouse
a11y 100 · perf budget met · OpenAPI snapshot ok + SDK regenerated · mypy/ruff/tsc/ESLint clean ·
knip/vulture clean. Prefer `nx affected -t lint test typecheck e2e`.
