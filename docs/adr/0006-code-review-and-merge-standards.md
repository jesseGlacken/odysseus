# ADR-0006: Code review & merge standards

- **Status:** Accepted
- **Date:** 2026-07-22
- **Deciders:** Repository owner
- **Supersedes:** none
- **Superseded by:** none

## Context

v2 is a quality-first rebuild where ~280K LOC are being restructured by both human and AI
agents. Without explicit review standards, review quality varies arbitrarily — some PRs are
rubber-stamped, others stall indefinitely. The v1 codebase received no formal PR review on
its deep internals and accumulated significant architectural debt as a result.

ADR-0004 mandates black-box tests at 100% coverage, but tests alone don't catch poor
architecture, security oversights, or layering violations. A complementary review standard
is needed.

Industry practices (Microsoft Code With Engineering Playbook, Google Engineering Practices)
prescribe mandatory PRs with automated gates and structured reviewer expectations.

## Decision

1. **Every change to `apps/` or `packages/` must go through a pull request.** Direct pushes
   to `main` are blocked for all contributors including `admin`. Exceptions: trivial
   documentation-only changes to `docs/` (not including ADRs), emergency hotfixes with a
   post-hoc review within 24 hours.

2. **Blocking automated gates must pass before human review begins:**
   - `pre-commit` (secrets, lint, format, structural bans)
   - `nx affected:lint` — zero errors
   - `nx affected:typecheck` (mypy --strict for Python, tsc for TypeScript) — zero errors
   - `nx affected:test` with `--passWithNoTests` — all tests pass
   - OpenAPI schema snapshot unchanged (or intentionally updated with reviewer confirmation)
   - SDK regeneration matches committed output

3. **PRs require at least one approving review from a human reviewer.** AI-generated
   reviews (automated code analysis) are supplementary, not sufficient. For PRs authored
   by an AI agent, the human reviewer must apply a higher standard: verify the agent's
   reasoning, not just the diff.

4. **Review focus areas (in priority order):**
   - **Security:** Does this change expose new attack surface, leak secrets, or weaken
     existing security controls?
   - **ADR compliance:** Does this change violate any Accepted ADR?
   - **Layering:** Are `packages/*` importing from `apps/*`? Is domain code importing
     from `routes/`? Are there new circular dependencies?
   - **Complexity:** Does this introduce any new function with CC > 20? (Must be justified
     in the PR description if so.) Does any file exceed 1,000 LOC?
   - **Test quality:** Are new tests black-box (exercising public surfaces)? Do they use
     accessible roles/labels for DOM queries? Are there new mocks of internal collaborators
     (reject if so)?
   - **Accessibility:** Does any new UI introduce an interactive widget not built on
     `packages/ui` primitives? Does it pass axe audit?

5. **Merge requirements:**
   - All automated gates green
   - At least one human approving review
   - No unresolved review comments flagged as blocking
   - Branch is up to date with `main` (linear history via rebase, no merge commits)
   - Author squashes commits into a single Conventional Commit message before merge

6. **Review turnaround expectations:**
   - PRs under 400 lines: reviewed within 1 business day
   - PRs 400–1,200 lines: reviewed within 2 business days
   - PRs over 1,200 lines: split before review; exceptions require prior agreement and
     may take longer

7. **ADR amendment PRs require a secondary reviewer.** Any PR that modifies, supersedes,
   or adds an ADR must be reviewed by at least one reviewer who did NOT co-author the PR.
   This prevents ADRs from being accepted without genuine scrutiny.

## Consequences

- **Positive:** consistent quality bar; AI agents have clear review expectations; ADRs
  cannot be changed unilaterally; review load is predictable.
- **Negative / costs:** 400-line PR limit encourages smaller, safer changes but adds
  overhead; human reviewer is a bottleneck for AI-authored PRs; may slow throughput
  compared to v1's direct-to-dev workflow.
- **Enforcement:** Branch protection rules on `main` (require PR, require approvals,
  require status checks); CODEOWNERS for ADR directory; PR template with review checklist.

## Alternatives considered

- **No formal PR process (v1 style).** Rejected: v1 accumulated architectural debt
  precisely because code was committed without review. v2's mandate is quality-first.
- **AI-only review.** Rejected: AI reviewers can catch patterns but lack the contextual
  judgment to assess architectural impact. Human review remains the final authority.
- **Two-human review on every PR (NASA style).** Rejected: disproportionate for this team
  size. The 400-line PR limit makes single-human review sufficient.
