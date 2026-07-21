# Odysseus — Quality-Gate Catalog

> Enforces [`docs/adr/0001`–`0005`](.). Companion to
> [`architecture-review.md`](../architecture-review.md) and
> [`migration-roadmap.md`](../migration-roadmap.md). **Research only — no hooks installed yet.**

Prose in `AGENTS.md` asks agents to comply; a red pipeline makes them. This catalogs the mechanical
checks that enforce each ADR clause — which tool, which stage, and whether it's safe to block or must
stay advisory.

## How enforcement works

Two axes decide where every gate belongs.

**Stage — where it runs** (assign each gate to the cheapest stage that still catches the defect; keep
`pre-commit` fast or developers disable it):

- **`pre-commit`** — fast, staged files only (format, lint, structural bans, secrets).
- **`pre-push`** — heavier, whole-project (full `mypy`/`tsc`, coverage on affected, drift checks).
- **`commit-msg`** — Conventional Commits.
- **CI** — too slow/env-heavy for a local hook (mutation, Lighthouse, axe E2E, full 100% coverage);
  mirror the whole suite here too via `pre-commit/action` or `pre-commit.ci`.

**Determinism — can it block?**

- **D — Deterministic / structural.** Exact pass/fail, no judgement. Safe to block once the tree is clean.
- **H — Heuristic.** Approximates intent, has false positives — stays advisory longer; tune/allowlist
  before it blocks.
- **C — CI-only.** Deterministic but far too slow for a local hook; never assigned to a commit stage.

## Catalog

### ADR-0001 — Contract-first

| ADR clause | Gate & tool | Stage | Det. |
|---|---|---|---|
| Every endpoint has a typed `response_model` | custom AST hook — flag `@router.<verb>` missing `response_model=` (465 decorators today) | pre-commit | D |
| OpenAPI schema is the source of truth | custom hook — dump `app.openapi()`, diff vs committed `packages/contracts/openapi.json` | pre-push | D |
| SDK generated, never hand-edited | custom hook — regen via `openapi-typescript`, `git diff --exit-code`; + CODEOWNERS lock | pre-push | D |
| No raw `fetch()` to the API from the FE | ESLint `no-restricted-globals`/`-syntax` — ban `fetch`/`XMLHttpRequest`/`axios` outside the SDK | pre-commit | D |
| Domain never imports `routes/` | import-linter (Python forbidden/layered contracts) | pre-commit | D |

### ADR-0002 — Monorepo boundaries

| ADR clause | Gate & tool | Stage | Det. |
|---|---|---|---|
| Module & dependency boundaries (`packages/*` ≠ import `apps/*`) | `@nx/enforce-module-boundaries` + project tags; import-linter for Python | pre-commit | D |
| The API is a proper installable package | `validate-pyproject` — assert a `[build-system]` table exists | pre-commit | D |
| Right project; no stray top-level modules | `knip` (TS) / import-linter unmatched-module contract | pre-push | H |

### ADR-0003 — Front-end standards

| ADR clause | Gate & tool | Stage | Det. |
|---|---|---|---|
| Don't hand-roll accessible widgets | `eslint-plugin-jsx-a11y` + `no-restricted-imports` (Radix/React-Aria only inside `packages/ui`) | pre-commit | H |
| Tailwind tokens; no ad-hoc/monolithic CSS | stylelint + `stylelint-declaration-strict-value` (color→token); large-CSS-file guard; `prettier-plugin-tailwindcss` | pre-commit | H/D |
| No hard-coded user-facing strings (i18n) | `eslint-plugin-i18next` `no-literal-string` (or formatjs) | pre-commit (advisory) | H |

### ADR-0004 — Testing, coverage & dead code

| ADR clause | Gate & tool | Stage | Det. |
|---|---|---|---|
| No coverage-exclusion pragmas | pygrep/forbid regex — ban `pragma: no cover`, `c8 ignore`, `istanbul ignore` | pre-commit | D |
| No unjustified `type: ignore`/`any`/`@ts-expect-error` | `mypy` `warn_unused_ignores`; ESLint `no-explicit-any`, `ban-ts-comment` | pre-commit | D |
| 100% line + branch coverage | `pytest-cov --branch fail_under=100`; `@vitest/coverage-v8` at 100 — via `nx affected` | pre-push / CI | D |
| Mutation score ≥ threshold | `mutmut`/`cosmic-ray` (Py) · `Stryker` (TS) | CI | C |
| Black-box only — no privates, no internal mocks | custom AST heuristic (flag `mock.patch("app.<internal>")`, underscore imports in tests) + `eslint-plugin-testing-library` | pre-commit (advisory) | H |
| Gherkin valid & every step defined | `gherkin-lint`/`reformat-gherkin`; `pytest-bdd` strict-undefined | pre-commit / CI | D |
| Dead code is deleted | `vulture` (Py, allowlist) · `knip` (TS) | pre-push | H |
| Strict types | `mirrors-mypy --strict`; `tsc --noEmit` | pre-push | D |

### ADR-0005 — Accessibility & performance

| ADR clause | Gate & tool | Stage | Det. |
|---|---|---|---|
| Static accessibility rules | `eslint-plugin-jsx-a11y` (strict config) | pre-commit | D (subset) |
| axe = 0 violations (runtime) | `vitest-axe` (component) · `@axe-core/playwright` (E2E) | pre-push / CI | C |
| Lighthouse a11y = 100 + perf budgets | `@lhci/cli` with `budgets.json` / assertions | CI | C |
| Manual assistive-tech audit | NVDA + VoiceOver — release checklist (not automatable) | release | — |

### Cross-cutting hygiene & security (mirror/extend existing CI)

| Gate | Tool | Stage | Det. |
|---|---|---|---|
| Secret detection | `gitleaks` (mirrors CI) | pre-commit | D |
| File hygiene | `pre-commit-hooks` (eof-fixer, trailing-ws, check-yaml/json/toml, merge-conflict, added-large-files, detect-private-key, check-ast) | pre-commit | D |
| Workflow & Dockerfile lint | `actionlint`, `zizmor`, `hadolint` (mirror CI) | pre-commit | D |
| Dependency vulnerabilities | `pip-audit` / `osv-scanner` | CI | C |
| Test deps kept out of runtime `requirements.txt` | custom hook — assert `pytest`/`httpx2`/`pytest-asyncio` absent | pre-commit | D |
| Conventional Commits | `commitlint` / `commitizen` | commit-msg | D |

## The six custom hooks to author

Everything above is a published hook *except* these — each a small `repo: local` hook (AST, regex, or
`git diff`). They make the contract-first and black-box ADRs mechanically enforceable rather than
aspirational.

1. **`response_model` checker** (AST · pre-commit) — parse `routes/**`; fail any route decorator without a declared response model. *(ADR-0001)*
2. **OpenAPI drift** (diff · pre-push) — dump `app.openapi()`; fail if it differs from the committed snapshot. *(ADR-0001)*
3. **SDK regen drift** (diff · pre-push) — regenerate the client; fail if the tree's SDK isn't identical. *(ADR-0001)*
4. **No-raw-`fetch` config** (ESLint · pre-commit) — restrict `fetch`/`axios` so only the SDK may reach the network. *(ADR-0001/0003)*
5. **Black-box heuristic** (AST · pre-commit) — flag tests that patch internal modules or import underscore-prefixed symbols. *(ADR-0004)*
6. **Runtime-deps guard** (regex · pre-commit) — fail if a test-only package appears in `requirements.txt`. *(cross-cutting)*

## What deliberately does NOT go in pre-commit

Mutation testing, Lighthouse, axe E2E, and the full 100% coverage run each need a build, a browser, or
the whole suite — seconds to minutes. Forcing them onto every commit is how teams end up running
`git commit --no-verify`. They live in CI (or `pre-push` on the *affected* graph only).

## Advisory-first, then flip

No gate blocks on day one. Each starts as a report and graduates to blocking **independently**, the
moment its own domain is clean — so early adoption never stalls behind unrelated debt.

**Mechanism:** roll the suite out as a CI-mirrored `pre-commit run --all-files` in a **non-required** job
(`continue-on-error`, plus `--exit-zero` where a tool supports it, e.g. ruff). Developers opt in with
`pre-commit install`. To **flip** a hook: drop `continue-on-error`, mark its check required, and enforce
`pre-commit install` via a bootstrap script. Give legacy debt a runway with a `mypy` baseline and a
`vulture` allowlist rather than blocking on it.

Advisory-first is more than caution here: the current tree has **22 `type: ignore`** and **4 `pragma: no
cover`** that would fail a full-repo ban immediately. Advisory mode surfaces the backlog without blocking
work; the flip happens after it's burned down. (Note: `pre-commit` checks only *staged* files by default,
so this bites only on a `--all-files` run.)

### Enablement order — tied to the migration phases

| When | Gates |
|---|---|
| **Now (works on today's monolith)** | file hygiene, ruff, gitleaks, pragma & type-ignore bans, `validate-pyproject`, runtime-deps guard, gherkin-lint scaffold, Conventional Commits — all advisory |
| **Phase 1 (contract-first)** | `response_model` checker, OpenAPI & SDK drift, import-linter — flip as each API domain is typed |
| **Phase 2 (backend SOLID)** | `mypy --strict`, coverage on affected, `vulture` — flip the Python bans to blocking once the tree is green |
| **Phase 3+ (front end)** | ESLint/jsx-a11y, stylelint, no-raw-fetch, testing-library, i18n, `vitest-axe`; Nx boundaries; mutation / Lighthouse / axe-E2E in CI. Flip per-domain as each goes green |
