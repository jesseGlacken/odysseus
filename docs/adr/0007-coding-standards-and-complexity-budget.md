# ADR-0007: Coding standards & cyclomatic-complexity budget

- **Status:** Accepted
- **Date:** 2026-07-22
- **Deciders:** Repository owner
- **Supersedes:** none
- **Superseded by:** none

## Context

The architecture review of v1 found 53 F-grade cyclomatic-complexity blocks, 14 files at
the maintainability floor, and a flat `src/` directory with no domain grouping. v2 uses
linters (ruff, ESLint) and type-checkers (mypy, tsc) to catch surface-level defects, but
linters don't enforce structural health — they won't stop a new 2,000-line God module or
a function with CC 200 from being committed.

AGENTS.md states "Small, single-responsibility units" and "no new God modules" but these
are prose aspirations. A formal ADR with CI-enforceable budgets makes them real.

Industry practice (Google, Microsoft, ThoughtWorks) converges on: max function length
~50-100 lines, max file size ~500-1,000 lines, max cyclomatic complexity ~10-20 for new
code, with budgets enforced mechanically.

## Decision

1. **File size budget — no new file shall exceed 1,000 LOC.** Existing files being
   refactored shrink toward this budget; files that were already below it must not grow
   past it. The budget is checked by `radon raw` or a custom CI gate.

2. **Function cyclomatic-complexity budget — no new function shall exceed CC 15.**
   Existing functions above CC 15 that are *modified* must decrease in complexity (the
   diff must show a net CC reduction). Rationale: radon's A/B band threshold is CC 10;
   15 gives room for genuine complexity while blocking the pathological tail. The v1
   worst case was CC 531 — this budget ensures v2 never repeats that.

3. **Module maintainability index — new modules must score ≥ 40 (radon mi).**
   Existing modules below 40 must not decrease further. The v1 had 14 files at MI 0.0
   (the floor); this prevents recurrence.

4. **Import order and grouping** (Python: isort-compatible via ruff; TypeScript: import/
   order rule). Imports are grouped (stdlib → third-party → first-party) with a blank
   line between groups. CI enforces via `ruff check` and ESLint.

5. **Naming conventions:**
   - Python: `snake_case` for modules, functions, variables; `PascalCase` for classes;
     `UPPER_SNAKE` for module-level constants.
   - TypeScript: `PascalCase` for components and types; `camelCase` for functions,
     variables, hooks (`useXxx`); `kebab-case` for UI component file names in
     `packages/ui` (shadcn convention), `PascalCase` for route components in `apps/web`.
   - No single-letter variable names except in comprehensions and loops with scope ≤ 5
     lines. Exceptions: `i`, `j` for index loops; `e` for exception handlers; `f` for
     file objects.

6. **Dead code is deleted immediately, not commented out.** ADR-0004 already mandates
   this for test coverage; this ADR extends it to the commit level: do not comment-out
   code and leave it. Delete it — git history preserves it if needed.

7. **Verbosity budgets:**
   - No parameter list shall exceed 7 positional parameters. Functions with more
     parameters must accept a typed configuration object (dataclass/dict for Python,
     interface/type for TypeScript).
   - No line shall exceed 100 characters (Python) or 120 characters (TypeScript). URL
     strings, long regex, and generated code are exempt.

8. **Documentation minimums:**
   - Every public module (`__init__.py` or `index.ts`) must have a one-line docstring
     describing its purpose.
   - Every public function/class must have a docstring describing its contract
     (parameters, return value, raised exceptions).
   - ADRs are the long-form documentation of architectural decisions; inline comments are
     for *why*, not *what*.

## Consequences

- **Positive:** structural health is mechanically enforced; no more God modules or
  mega-functions can emerge undetected; naming is consistent across languages; reviewers
  have clear criteria.
- **Negative / costs:** some legitimate complex functions (e.g., state-machine dispatch,
  parser combinators) may exceed CC 15 and need explicit justification. The budget is a
  gate, not an absolute ban — exceptions require a comment with the `reason:` keyword
  explaining why the budget must be exceeded.
- **Enforcement:** `radon cc --max-cc 15` as a pre-commit gate (advisory initially,
  blocking in Phase 2); `radon raw --max-loc 1000` for file sizes; ruff `isort` rules;
  ESLint import/order; custom gate for parameter count. CI bailout on regression.

## Alternatives considered

- **No budgets — rely on code review.** Rejected: v1 proves review alone doesn't scale
  to ~280K LOC. Budgets are the backstop when human attention wanders.
- **Stricter budgets (CC 10, 500 LOC).** Rejected for now: too aggressive for the
  migration phase. The proposed budgets can be tightened in a follow-up ADR once the
  codebase is clean.
- **Prettier-only formatting (no budgets).** Rejected: formatting is cosmetic; budgets
  measure structure. We apply both.
