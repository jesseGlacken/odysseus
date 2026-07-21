# Architecture Decision Records

This directory holds the **Architecture Decision Records (ADRs)** that govern the
Odysseus v2 quality-first rebuild. An ADR captures a single significant decision, its
context, and its consequences. Once an ADR is **Accepted**, it is binding on all new
work — human or agent — until it is explicitly **Superseded** by a newer ADR.

> These ADRs are the **source of truth**. The agent instruction files at the repo root
> and in tool-specific locations (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`,
> `.github/copilot-instructions.md`, `.cursor/rules/`, `.clinerules/`, `.windsurfrules`)
> summarise these decisions so coding assistants apply them, but they defer to the ADRs
> here on any conflict.

## Index

| ADR | Title | Status |
|-----|-------|--------|
| [0001](0001-keep-and-harden-fastapi-contract-first.md) | Keep & harden FastAPI; make it contract-first | Accepted |
| [0002](0002-nx-polyglot-monorepo.md) | Adopt an Nx polyglot monorepo | Accepted |
| [0003](0003-react-spa-shadcn-react-aria.md) | React SPA on shadcn/ui + React Aria | Accepted |
| [0004](0004-testing-standards-blackbox-100pct-mutation.md) | Testing standards: black-box, Gherkin, 100% coverage, mutation | Accepted |
| [0005](0005-accessibility-and-performance.md) | Accessibility (WCAG 2.2 AA) & performance as gates | Accepted |

New records use [`0000-template.md`](0000-template.md) and the next free number.

## Status lifecycle

`Proposed` → `Accepted` → (`Deprecated` | `Superseded by ADR-XXXX`). Never edit an
Accepted ADR's decision in place to reverse it — write a new ADR that supersedes it and
update the old one's status. This preserves the decision history.

## How these are enforced

Instruction files make the rules *visible* to coding agents; they do not by themselves
*guarantee* compliance. Enforcement is layered:

1. **ADRs** (this directory) — the binding decisions.
2. **Agent instruction files** — surface the rules to every assistant at authoring time.
3. **CI gates (the hard backstop)** — the roadmap's blocking checks: 100% line+branch
   coverage, mutation score, `axe`/Lighthouse budgets, `mypy --strict`/`tsc`, `ruff`/ESLint,
   OpenAPI schema snapshot, and dead-code (`knip`/`vulture`). Prose can be ignored; a red
   pipeline cannot.

An agent (or human) that believes an ADR is wrong should **propose a superseding ADR**,
not quietly work around it.
