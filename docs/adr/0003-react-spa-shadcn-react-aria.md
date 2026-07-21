# ADR-0003: React SPA on shadcn/ui + React Aria

- **Status:** Accepted
- **Date:** 2026-07-21
- **Deciders:** Repository owner
- **Supersedes:** none
- **Superseded by:** none

## Context

The v1 front end is ~133k LOC of framework-free vanilla ES modules with no build, no tests,
no lint, single files over 11k lines, and one 40k-line stylesheet. v2 requires a reactive,
componentised front end that can meet **uncompromising WCAG 2.2 AA** (ADR-0005) and a
Lighthouse budget, while honouring SOLID and avoiding vendor lock-in.

The decisive requirements: accessibility rigor favours a headless *primitive* layer with a
strong a11y track record (Adobe **React Aria**, and **Radix** — the basis of shadcn/ui) over
pre-styled kits; SOLID/no-lock-in favours **shadcn/ui's own-the-code model** (components are
generated *into* the repo, not consumed as an opaque dependency); the Lighthouse target
favours minimal shipped JS and no added Node runtime in production.

## Decision

1. **`apps/web` is a React 19 + TypeScript SPA built with Vite**, served as static assets by
   the FastAPI app (no separate Node SSR server in production).
2. **`packages/ui` is the owned component library.** It uses **shadcn/ui on Radix primitives**
   as the default, and **Adobe React Aria Components** for complex widgets (combobox, date
   picker, data grid, listbox, menus) where its assistive-tech coverage leads. Components are
   owned source in-repo and may be refactored to satisfy SOLID and a11y.
3. **Styling is Tailwind + CSS custom-property design tokens**, themed for light and dark. No
   ad-hoc per-component stylesheets; no return to a monolithic global CSS file.
4. **Server state goes through TanStack Query over the generated SDK** (ADR-0001) — this is
   the sanctioned replacement for the 876 raw `fetch()` calls. Routing uses TanStack Router.
5. **Accessible widgets are never hand-rolled.** Build on `packages/ui` (Radix/React Aria);
   do not reimplement a dropdown, dialog, tab set, or combobox from raw `div`s.

## Consequences

- **Positive:** best-in-class accessibility primitives; owned, SOLID-refactorable components;
  large ecosystem and hiring pool; small deploy surface (static SPA).
- **Negative / costs:** a pure SPA must work to hit a perfect *performance* score on heavy
  routes (editor, chat, gallery) — see ADR-0005; the team owns (and must maintain) the copied
  component source.
- **Enforcement:** ESLint `jsx-a11y` + `vitest-axe` + `axe-core/playwright` (0 violations);
  Lighthouse CI budgets; a review rule that new interactive UI uses `packages/ui` primitives.

## Alternatives considered

- **React + React Aria only (no shadcn).** Viable and maximally rigorous, but more verbose and
  a smaller component ecosystem; we adopt React Aria *selectively* for hard widgets instead.
- **SvelteKit + shadcn-svelte.** Best default bundle size, but a smaller and less battle-tested
  a11y-primitive ecosystem and talent pool.
- **Angular / Vue / MUI / Chakra.** Rejected: heavier defaults or pre-styled kits that are
  harder to force to *uncompromising* AA and to own outright.
