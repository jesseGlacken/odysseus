# ADR-0008: Security architecture

- **Status:** Accepted
- **Date:** 2026-07-22
- **Deciders:** Repository owner
- **Supersedes:** none
- **Superseded by:** none

## Context

v1 has a strong existing security posture: Trivy container scanning, gitleaks secret
detection, zizmor workflow hardening, hadolint Dockerfile lint, pip-audit dependency
audit, SSRF protection tests, prompt-injection defences, secret encryption at rest,
2FA support, and per-route privilege gating. These are implemented and tested but
have not been captured as architectural decisions.

v2 add a public API surface (typed OpenAPI), a generated TypeScript SDK, a monorepo
with new package boundaries, and AI coding agents that generate code. Each of these
introduces new security considerations that need explicit architectural guidance.

Industry standards (OWASP ASVS, NIST SP 800-218 SSDF, Google SLSA) converge on:
defence-in-depth, least privilege, secure defaults, and supply-chain integrity.

## Decision

1. **The existing v1 security suite carries forward into v2 and is strengthened,
   not weakened.** Every security tool in the current CI pipeline (Trivy, gitleaks,
   zizmor, hadolint, pip-audit) remains a blocking gate. No security regression is
   acceptable.

2. **Secrets must never be committed to the repository.** This is enforced by
   gitleaks at pre-commit. Secrets include: API keys, tokens, passwords, private
   keys, database connection strings with credentials, OAuth client secrets, and
   signing keys. Secrets belong in `.env` (gitignored), environment variables, or a
   secrets manager.

3. **The generated TypeScript SDK (`packages/client-sdk`) is the sole channel for
   frontend-to-backend communication.** No raw `fetch()`, `axios`, or `XMLHttpRequest`
   calls are permitted outside the SDK. This ensures all API access respects auth
   headers, CSRF tokens, and content-type validation.

4. **All authenticated endpoints enforce owner-scoping.** Multi-user isolation is
   mandatory. The Persona bug (global preset singleton, cross-user state leak) is a
   concrete example of the kind of defect this prevents — no user's action must
   affect another user's state without explicit authorization.

5. **Input validation is layered:**
   - **Route layer:** Pydantic v2 request models validate type, range, length, and
     format before any handler logic executes.
   - **Domain layer:** Business rules validate invariants (e.g., email owner matches
     session user).
   - **Infrastructure layer:** SQLAlchemy parameterised queries prevent injection
     (no raw string interpolation for SQL). Shell commands validate arguments against
     allowlists.
   - **External boundaries:** URL fetching validates scheme (https only), resolves
     to non-internal IPs, enforces timeout and size limits. IMAP connections use
     STARTTLS/TLS.

6. **Content Security Policy (CSP) is enforced via SecurityHeadersMiddleware.**
   The CSP header restricts script sources, prevents inline scripts (except nonce-
   gated), and limits connect-src to the API origin. The nonce is rotated per-request.

7. **Supply-chain security:**
   - `pip-audit` scans Python dependencies on every CI run. CVEs with severity
     ≥ HIGH block the build.
   - `npm audit` scans JavaScript dependencies. CVEs with severity ≥ HIGH block
     the build.
   - Docker images are scanned by Trivy. CVEs with severity ≥ CRITICAL block the
     build.
   - Third-party assets (KaTeX, Mermaid) are loaded from CDN only; a future ADR or
     ticket will vendor them.

8. **Authentication and session management:**
   - Session IDs are cryptographically random (secrets.token_urlsafe).
   - Session cookies are HttpOnly, Secure (when behind HTTPS), and SameSite=Lax.
   - Password hashing uses bcrypt with work factor ≥ 12.
   - 2FA uses TOTP with SHA-1 or SHA-256 (RFC 6238).
   - Session tokens for API access expire and must be rotated.

9. **Threat model is maintained as a living document.** The existing THREAT_MODEL.md
   is updated whenever a new feature changes the attack surface. Threat modelling
   is part of the PR template for changes to auth, file upload, shell execution,
   or external API integration.

## Consequences

- **Positive:** security posture is explicit, auditable, and enforced; new features
  inherit secure defaults; supply chain is monitored continuously.
- **Negative / costs:** security gates add CI latency; strict input validation and
  owner-scoping require more test authoring; threat-model updates add process overhead.
- **Enforcement:** gitleaks, Trivy, zizmor, hadolint, pip-audit, and npm audit are
  blocking CI gates. CSP enforcement via middleware. PR template includes threat-model
  checkbox. CODEOWNERS can designate security-sensitive paths for mandatory review.

## Alternatives considered

- **Relax security gates to advisory.** Rejected: v1 has already proven these tools
  can run blocking. Security is not a place for advisory-only enforcement.
- **Drop gitleaks in favour of GitHub secret scanning.** Rejected: gitleaks runs
  pre-commit (before secrets reach the remote) and catches patterns GitHub scanning
  may miss. Both can coexist.
- **Vendor all CDN assets.** Accepted in principle, deferred to a future ticket
  (already on the roadmap). This ADR acknowledges the risk and defers the action.
