# ADR-0004: Testing standards — black-box, Gherkin, 100% coverage, mutation

- **Status:** Accepted
- **Date:** 2026-07-21
- **Deciders:** Repository owner
- **Supersedes:** none
- **Superseded by:** none

## Context

v1 had 47.5% backend coverage (routes 36%), effectively 0% front-end coverage, and no UI/E2E
tier. v2 treats test quality as a first-class product requirement. The owner's mandate:
black-box testing only, at all pyramid levels, described in Gherkin mapped to product
requirements, with a fully passing, 100%-covered suite; any code the suite cannot exercise is
dead and is deleted.

"100% coverage" and "black-box only" are in deliberate tension — that tension is the design.
Coverage cannot be reached by testing internals, so it must be driven entirely through public
surfaces; anything unreachable that way is unreachable by users too. Mutation testing is what
prevents "100% coverage" from being satisfied by assertion-free tests.

## Decision

1. **Black-box only.** Tests exercise **public surfaces only**:
   - Back end: HTTP endpoints (via the app / httpx / TestClient), with real dependencies or
     testcontainers — not internal functions, private helpers, or implementation detail.
   - Front end: the DOM queried by **role / accessible name / label** (Testing Library,
     Playwright) — not component internals, instance state, or snapshot-of-implementation.
   - **No reaching into privates** and **no mocking of internal collaborators** to manufacture
     coverage. External boundaries (network, clock, filesystem) may be controlled.
2. **Gherkin as the spec.** Behaviour is described in `.feature` files under `features/`, in
   Given/When/Then, mapped to product requirements. The same features drive back-end tests
   (`pytest-bdd`) and E2E (`playwright-bdd`), so requirements and tests are one artifact.
3. **Full pyramid, black-box at every level:** component/unit (behaviour via public API/DOM) →
   integration/contract (API against real deps; OpenAPI snapshot) → E2E (Playwright journeys).
4. **100% line AND branch coverage is a blocking gate.** `coverage.py --branch`
   (`fail_under=100`) for Python; `@vitest/coverage-v8` at 100% for TypeScript. **Do not lower
   thresholds and do not add coverage-exclusion pragmas** (`# pragma: no cover`, `/* c8 ignore */`,
   `istanbul ignore`) to dodge the gate.
5. **Mutation testing is a blocking gate.** `mutmut`/`cosmic-ray` (Python) and `Stryker`
   (TypeScript) must meet the agreed score. When mutants survive, **add real assertions** — do
   not annotate them away.
6. **Dead code is deleted, not excused.** Code unreachable by the black-box suite is removed
   (`knip` for TS, `vulture` for Python) **after a human confirms** no black-box scenario
   *should* reach it — if one should, the missing test is the defect, not the code. Never
   comment out or ignore-annotate to satisfy the reaper.

## Consequences

- **Positive:** tests survive refactors (they bind to behaviour, not structure); coverage is
  meaningful (mutation-checked); the codebase cannot silently accrete unreachable code; specs
  and tests stay in sync with product requirements.
- **Negative / costs:** black-box + 100% is demanding to author and can be slower; some
  hard-to-reach error branches force either a real triggering scenario or deletion.
- **Enforcement:** CI gates for branch coverage, mutation score, and dead-code scanners; PR
  review checks that new tests query public surfaces and that features trace to requirements.

## Alternatives considered

- **100% line coverage only / allow white-box unit tests.** Rejected: line-only coverage and
  implementation-coupled tests are exactly what let v1 pass while the real API surface went
  untested.
- **Coverage without mutation.** Rejected: coverage alone is satisfiable by tests that assert
  nothing.
