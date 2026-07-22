# ADR-0009: API versioning & backward compatibility

- **Status:** Accepted
- **Date:** 2026-07-22
- **Deciders:** Repository owner
- **Supersedes:** none
- **Superseded by:** none

## Context

ADR-0001 establishes that the OpenAPI schema is the single source of truth and that the
frontend consumes the API only through the generated TypeScript SDK. However, ADR-0001
does not address what happens when the API *changes* — how breaking changes are managed,
how deprecation is communicated, or how the versioned contract interacts with the SDK.

The v1 API has 465 endpoints serving 876 raw `fetch()` calls. During v2 migration, these
endpoints are being typed (Pydantic `response_model`) and the schema is emitted and
snapshot-tested. Typing inherently clarifies the API surface and may reveal fields that
were accidentally exposed or inconsistently named. This creates tension: we must not break
the v1 frontend during the strangler migration, even as we clean the contract.

Industry standards (SemVer, Google AIP-180/181, Stripe API versioning, RFC 9457
Deprecation header) converge on: major version in the path, sunset headers, and
documented migration windows.

## Decision

1. **The API uses path-based versioning.** The initial version is `v1`:
   - v1 is the existing API, now typed with `response_model`. The v1 OpenAPI schema
     lives at `/api/v1/openapi.json`.
   - v2 is reserved for future use. When a breaking change is required, it is
     introduced as `/api/v2/` while v1 remains available during a deprecation window.
   - The current endpoints (`/api/chat`, `/api/auth/login`, etc.) preserve their
     existing paths for backward compatibility during Phase 0–4. These are treated
     as aliases to the `v1` endpoints. After the v1 frontend is fully retired
     (Phase 4 completion), a future ADR will decide whether to route these aliases
     to a preferred version.

2. **Backward-compatible changes do NOT require a version bump.** A change is
   backward-compatible if:
   - It adds a new endpoint or a new optional field to an existing response.
   - It adds a new optional query parameter or request body field.
   - It relaxes validation (e.g., widening a `max_length`).
   - It adds a new HTTP method to an existing path.

3. **Breaking changes require a new API version.** A change is breaking if:
   - It removes or renames an endpoint, field, or parameter.
   - It changes a field's type or tightens validation (e.g., narrowing `max_length`).
   - It changes authentication requirements.
   - It changes response status codes for existing inputs.
   - It removes a previously supported HTTP method.

4. **Deprecated endpoints carry a deprecation window of at least one major release.**
   When an endpoint is deprecated:
   - The response includes a `Sunset` header (per RFC 9457) with the planned removal date.
   - The OpenAPI schema marks the endpoint as `deprecated: true` with a `x-sunset`
     extension.
   - The generated SDK emits a deprecation warning at compile time (TypeScript
     `@deprecated` JSDoc annotation).
   - The deprecation is documented in the migration notes for that release.

5. **The OpenAPI schema is the contract for compatibility verification.** The snapshot
   test (`packages/contracts/tests/openapi-snapshot.test.ts`) fails on any unintended
   schema change. Intended changes must be accompanied by a version bump or a documented
   backward-compatible justification in the PR description.

6. **SDK generation always targets a specific API version.** A future enhancement
   (deferred) will support generating multiple SDK versions from the same schema by
   filtering paths under `/api/v1/` vs `/api/v2/`.

## Consequences

- **Positive:** breaking changes are deliberate and documented; v1 frontend is
  protected during migration; deprecation window gives consumers time to upgrade;
  compatibility is mechanically verified.
- **Negative / costs:** path-based versioning means eventually maintaining two API
  surface areas during deprecation windows; the OpenAPI schema must track deprecation
  metadata; SDK consumers see compile-time deprecation warnings.
- **Enforcement:** OpenAPI snapshot test fails on unintended schema changes; PR
  template includes a backward-compatibility checkbox; the breaking-change checklist
  gates any API change that removes or renames fields.

## Alternatives considered

- **Header-based versioning (Accept: application/vnd.odysseus.v2+json).**
  Rejected: harder to test, harder to document in OpenAPI, invisible in logs.
  Path-based versioning is the industry consensus for REST APIs.
- **No versioning — just never break the API.** Rejected: idealistic. The v2
  migration already identified multiple breaking changes (per-user preset scoping,
  typed response models that may constrain previously loose dict returns). A
  versioning strategy is needed.
- **GraphQL instead of versioning.** Rejected: ADR-0001 already chose REST/FastAPI.
  GraphQL is a different architecture decision entirely.
