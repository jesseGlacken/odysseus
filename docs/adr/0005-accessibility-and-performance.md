# ADR-0005: Accessibility (WCAG 2.2 AA) & performance as gates

- **Status:** Accepted
- **Date:** 2026-07-21
- **Deciders:** Repository owner
- **Supersedes:** none
- **Superseded by:** none

## Context

Accessibility is a first-class requirement for v2, not a late audit. v1 had partial awareness
(some ARIA) but no enforcement and no i18n. The owner's mandate is **uncompromising WCAG 2.2
AA** and a **100% Lighthouse** target. A perfect performance score on every heavy route (rich
editor, streaming chat, image gallery) as a pure SPA is aspirational, so the performance
commitment is scoped and budgeted rather than blanket, while accessibility is absolute.

## Decision

1. **WCAG 2.2 AA is non-negotiable on every route and component.**
   - Every UI change ships with **`axe` = 0 violations** (component tests via `vitest-axe`,
     E2E via `axe-core/playwright`) and **Lighthouse accessibility = 100**.
   - Use **semantic HTML** and the accessible primitives in `packages/ui` (Radix / React Aria,
     per ADR-0003). Do not hand-roll accessible widgets.
   - Keyboard operability, visible focus, correct names/roles/labels, and reduced-motion
     support are required. Colour is never the sole information carrier; text/tokens meet AA
     contrast in **both** light and dark themes.
   - New user-facing strings go through the i18n layer (no hard-coded copy in components).
   - A **manual assistive-technology audit** (NVDA + VoiceOver) signs off each release.
2. **Performance is budgeted in CI.**
   - **Lighthouse performance = 100 on core routes** (defined per release), enforced as a
     per-route budget (LCP / CLS / TBT / bundle size). A route that cannot meet budget as an
     SPA is escalated to SSR/islands for that route — the budget is not simply waived.
   - Do not add heavy dependencies or main-thread-blocking work without a budget check; prefer
     code-splitting and lazy loading. Best-practices and SEO Lighthouse categories target 100.

## Consequences

- **Positive:** the product is usable by everyone and stays fast; accessibility regressions are
  caught at authoring time, not in a pre-release scramble.
- **Negative / costs:** a11y-correct components take more care; hitting perf budgets on the
  heaviest routes may force per-route SSR/islands work.
- **Enforcement:** `axe`/Lighthouse CI gates (a11y hard-fail; perf budget per route); ESLint
  `jsx-a11y`; the per-release manual AT audit as a release checklist item.

## Alternatives considered

- **Audit accessibility before release instead of gating per PR.** Rejected: that is how v1
  accumulated debt; AA must be enforced continuously.
- **Blanket "100 Lighthouse everywhere, always."** Rejected as stated: honest budgeting per
  route (with SSR escalation) is more truthful and achievable than a claim the heaviest routes
  can't keep; accessibility, unlike raw performance, is held absolute.
