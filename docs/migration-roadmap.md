# Odysseus v2 — Migration Roadmap

> Companion to [`architecture-review.md`](architecture-review.md). Baseline metrics from working tree
> `dev @ bda7f40`. Durations are planning estimates for a small dedicated team; a single engineer
> multiplies them.

A quality-first pivot: a decoupled Nx monorepo, a contract-first FastAPI core, a fully accessible React
front end, and one governing rule — nothing ships unless it is proven by black-box tests, at 100%
coverage, mutation-checked, and WCAG AA clean.

The four locked decisions are recorded as ADRs: [0001](adr/0001-keep-and-harden-fastapi-contract-first.md)
(keep & harden FastAPI, contract-first), [0002](adr/0002-nx-polyglot-monorepo.md) (Nx monorepo),
[0003](adr/0003-react-spa-shadcn-react-aria.md) (React + shadcn/ui + React Aria),
[0004](adr/0004-testing-standards-blackbox-100pct-mutation.md) (testing standards),
[0005](adr/0005-accessibility-and-performance.md) (accessibility & performance).

## The governing law of the repo

These are blocking CI gates, not aspirations:

- **Contract-first** — the OpenAPI schema is the source of truth; the TS SDK is generated, never
  hand-written; the schema is snapshot-gated.
- **Black-box only** — tests touch public surfaces (HTTP; DOM by role/name). `.feature` files are
  product requirements.
- **100% coverage** — lines *and* branches. Unreachable code is dead code → deleted, not excused.
- **Mutation testing** — Stryker / mutmut prove the black-box tests actually detect behavior changes.
- **Accessibility** — WCAG 2.2 AA: axe = 0 violations + Lighthouse a11y = 100 + manual AT audit per release.
- **Performance** — per-route Lighthouse budgets; perf = 100 on core routes.

**The hard part, named — reconciling "100% coverage" with "black-box only":** you cannot reach 100%
branch coverage by testing internals if internals aren't tested directly, so coverage is driven entirely
through the API and the DOM. Any branch no black-box test can reach is unreachable by users too → it is
deleted. Mutation testing stops "100% coverage" from being satisfied by tests that assert nothing.

## Target structure (Nx workspace)

```
apps/
  web/          # React 19 + Vite SPA, served as static assets by FastAPI
  api/          # FastAPI, relocated from repo root; src-layout + real build-system
packages/
  contracts/    # openapi.json (source of truth) + schema snapshot tests
  client-sdk/   # generated typed TS client — replaces all 876 raw fetch() calls
  ui/           # shadcn/ui (owned) on Radix + React Aria widgets + design tokens
  config/       # shared eslint / tsconfig / tailwind / vitest / ruff presets
features/       # Gherkin .feature files (product requirements; shared FE+BE)
e2e/            # Playwright + playwright-bdd (black-box)
tools/          # Nx generators, codegen, migration scripts
docs/           # ADRs, C4 diagrams, docs site
```

The only coupling between front end and back end is the generated SDK, produced from the OpenAPI
contract the API emits. The Python API is also re-layered internally per the review: flat `src/` →
`domain/`/`agent/`/`infra/`/`llm/`; `routes/` fully sub-packaged; a repository layer over
`core/database.py`; `src→routes` imports removed.

## Best-in-class tooling

| Concern | Choice |
|---|---|
| Monorepo | Nx + `@nxlv/python` (FastAPI project), Nx affected + remote cache |
| FE runtime | React 19, TypeScript (strict), Vite, TanStack Query + Router |
| Components / a11y | shadcn/ui on Radix, React Aria Components for hard widgets, Tailwind + CSS vars |
| Contract / SDK | FastAPI OpenAPI → openapi-typescript + openapi-fetch (or Orval), schema snapshot test |
| BE tests | pytest + pytest-bdd, coverage.py `--branch` (`fail_under=100`), mutmut / cosmic-ray |
| FE tests | Vitest + Testing Library + vitest-axe, `@vitest/coverage-v8` (100%), Stryker |
| E2E | Playwright + playwright-bdd, `axe-core/playwright`, Lighthouse CI budgets |
| Lint / types / dead code | ruff, mypy --strict, ESLint (typescript-eslint + jsx-a11y), Prettier, knip (TS), vulture (Py) |
| Observability | OpenTelemetry (`opentelemetry-instrumentation-fastapi` + web SDK) → OTLP → Prometheus/Grafana/Tempo/Loki; web-vitals RUM; self-hosted GlitchTip/Sentry |
| Docs | Docusaurus (or MkDocs Material), Storybook + addon-a11y, TypeDoc, ADRs, C4 via Structurizr/Mermaid, Redoc/Scalar |
| CI | GitHub Actions — keep the existing security suite (Trivy, gitleaks, zizmor, hadolint, pip-audit); add quality gates as blocking |

## Phases (target: v2.0 major release)

Effort assumes a small dedicated team. Phases 1–3 overlap once the test net exists.

| Phase | Duration | Focus | Exit |
|---|---|---|---|
| **0 — Foundation & guardrails** | 2–4 wks | Nx workspace; relocate backend into `apps/api` with a real build-system, behaviour unchanged. CI scaffolding advisory-first (ruff, mypy, branch-coverage report, radon "no new CC>15", ESLint/Prettier/tsc). ADRs, C4 baseline, Gherkin conventions, OTel skeleton (reuse `core/middleware.py`, `core/log_safety.py`). | monorepo boots · legacy app still runs · gates reporting |
| **1 — Contract-first backend** | 4–6 wks | Typed `response_model`s across 465 endpoints, domain by domain (seed from `src/request_models.py`). Emit & snapshot `openapi.json`; generate the SDK. `.feature` files per domain as black-box API tests, route coverage 36% → 100%. Branch + mutation gates flip to blocking per domain. | typed contract + SDK + acceptance suite · coverage climbing |
| **2 — Backend decoupling & SOLID** | 4–6 wks (overlaps) | Decompose `stream_agent_loop` (531) and `_stream_llm_inner` (216); regroup flat `src/`; repository layer to invert `core.database` (DIP); remove 36 `src→routes` imports; split `database.py` **last**. | no God modules · no layering violations · gates blocking |
| **3 — Front-end foundation** | 4–6 wks | Scaffold `apps/web` + `packages/ui` (shadcn/Radix + React Aria + Tailwind tokens, light/dark, Storybook + a11y addon). Every component ships axe tests + Gherkin specs. Wire SDK behind TanStack Query (retires 876 fetches). Lighthouse + axe budgets in CI. | accessible component library + app shell on the typed API |
| **4 — Feature migration (vertical slices)** | 2–4 months | One domain at a time (chat, documents, email, cookbook, notes/calendar, gallery, settings): shared `.feature` → Playwright E2E → React screens on `packages/ui` → consume SDK; SSE via SDK helpers. Delete each legacy `static/js` module when its features pass. Each slice: 100% line+branch, mutation ≥ threshold, axe 0, Lighthouse budget. | legacy front-end retired module-by-module · SPA at parity |
| **5 — Harden, observe, cut over → v2.0** | 3–4 wks | Full OTel (FE web-vitals RUM + BE traces) + dashboards; self-hosted error tracking. Manual WCAG 2.2 AA audit (NVDA/VoiceOver), Lighthouse 100 on core routes, repo-wide mutation run. Delete remaining dead code; remove test deps from runtime `requirements.txt`. Publish docs site. | v2.0 shipped · docs live · dead code gone |

## Definition of done — every slice

Blocking CI gates, all must pass:

| Gate | Bar | Tool |
|---|---|---|
| Coverage | 100% lines *and* branches | coverage.py --branch · v8 |
| Mutation | score ≥ threshold | mutmut / cosmic-ray · Stryker |
| Accessibility | axe 0 violations · Lighthouse a11y = 100 | vitest-axe · axe/playwright · LHCI |
| Performance | per-route budget met | Lighthouse CI |
| Contract | schema snapshot unchanged / reviewed | openapi snapshot test |
| Types & lint | zero errors | mypy --strict · ruff · tsc · ESLint |
| Dead code | none unreachable | knip · vulture |
| E2E traceability | Gherkin feature suite green | playwright-bdd |
| Manual (per release) | AT audit sign-off | NVDA + VoiceOver |

End-to-end smoke: `nx run-many -t test lint typecheck e2e` green; `nx affected` in PR CI;
`docker compose up` serves the new SPA from FastAPI with OTel traces visible in Grafana/Tempo.

## Risks & honest caveats

- **This is a re-platform, not a refactor.** ~133k lines of front-end behaviour must be re-specified as
  Gherkin and rebuilt. The biggest risk is treating Phase 4 as "porting"; it is "rewriting to a spec."
  Keep slices small and vertical; never let legacy and new front ends both own a feature at once.
- **100/100/100/100 Lighthouse is aspirational on heavy routes.** Treat perf = 100 as a *core-route*
  commitment enforced by budgets, escalating a specific route to SSR/islands only if it can't make
  budget otherwise. A11y = 100 is non-negotiable everywhere.
- **"Delete uncovered code" needs a human in the loop.** Coverage can't tell "genuinely dead" from
  "reachable only by an untested path." Before deleting, confirm no black-box scenario *should* exercise
  it — otherwise the missing test is the defect. Wire this as a review step, not an automated reaper.
- **You are not starting from zero.** The strong security CI, the 81k-line Python test corpus
  (re-castable as black-box), the existing auth/2FA, and the internal architecture spec carry forward.
  The investment concentrates on the contract, the SOLID cleanup, and the new front end.
