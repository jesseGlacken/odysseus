# ADR-0001: Keep & harden FastAPI; make it contract-first

- **Status:** Accepted
- **Date:** 2026-07-21
- **Deciders:** Repository owner
- **Supersedes:** none
- **Superseded by:** none

## Context

Odysseus v1 is a ~117k-LOC Python/FastAPI backend with an ~81k-LOC test corpus and a
Python-only AI ecosystem (fastembed, chromadb-client, caldav, mcp, pdf tooling). The v2
rebuild fully decouples the front end from the back end. The backend could be rewritten
in TypeScript for a single-language monorepo, but that would discard the test investment
and force re-solving the Python AI stack.

A review of the current API found only **3 of 67 route files** declare a `response_model`
(3 uses across **465 endpoints**) and **no OpenAPI schema is committed** — so the API is
effectively untyped at its boundary, and the front end reaches it through **876 hand-rolled
`fetch()` calls** with no client.

## Decision

1. **The backend stays FastAPI (Python).** It is preserved and hardened, not rewritten. It
   lives at `apps/api/` in the monorepo (see ADR-0002).
2. **The API is contract-first.** The **OpenAPI schema is the single source of truth** for
   the front-end/back-end boundary:
   - Every HTTP endpoint declares a typed `response_model` and typed request models
     (Pydantic v2). Untyped/`dict`-returning endpoints are not acceptable for new or
     migrated code.
   - The schema is exported to `packages/contracts/openapi.json` and **snapshot-tested** in
     CI; an unintended schema change fails the build.
   - The typed TypeScript client in `packages/client-sdk/` is **generated** from that
     schema (openapi-typescript + openapi-fetch). It is never hand-written or hand-edited.
   - The front end consumes the API **only** through the generated SDK — no raw `fetch()`
     to backend routes.
3. **Backend layering is enforced.** Domain/agent/LLM code must not import from `routes/`
   (the current 36 `src→routes` back-imports are removed during migration). Data access goes
   through a repository layer, not direct `core.database` calls scattered across the code.

## Consequences

- **Positive:** keeps the Python AI ecosystem and the existing test value; gives the front
  end fully typed, always-in-sync API access; makes breaking API changes visible in CI.
- **Negative / costs:** typing 465 endpoints is real work, done domain-by-domain; two
  runtimes (Python API + Node build tooling) coexist in the repo.
- **Enforcement:** OpenAPI snapshot test; a lint/review rule that new endpoints must set
  `response_model`; an import-linter rule forbidding `routes` imports from domain packages;
  SDK regenerated in CI and diffed.

## Alternatives considered

- **Rewrite in TypeScript (NestJS).** Rejected: discards 81k LOC of tests and the Python AI
  stack; multi-quarter cost with high risk.
- **Strangler TS gateway over the Python core.** Rejected for now: adds a network hop and a
  second production runtime for little benefit while the Python core is retained anyway.
