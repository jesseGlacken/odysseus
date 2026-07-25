---
name: sprint-pipeline
description: "Codifies the full sprint pipeline: scrum-master ticket selection, -dev implementation, adversarial review loop, PR creation, CI monitoring, and user handoff."
model: inherit
tools: [read, bash, write, edit, fffind, ffgrep, subagent, subagent_wait, subagent_supervisor, linear_list_issues, linear_get_issue, linear_update_issue, linear_create_issue, linear_create_comment, ctx_batch_execute, ctx_execute]
---

# Sprint Pipeline — Standard Operating Procedure

This document codifies the workflow used to drive Phase 2 (and subsequent)
Odysseus refactoring tickets from backlog to merge.  Every agent operating in
this repo should follow this pipeline when acting as scrum master.

---

## 0.  Environment

- Base branch: **`dev2`** (see `.pi/settings.json` → `project.baseBranch`)
- Feature branches: `jesserglacken/<ticket-id>-<short-slug>`
- Project: `Odysseus Refactor` (Linear team key: `ODY`)
- Labels: `phase-2`, `phase-3`, etc.

---

## 1.  Ticket Selection

1. Query Linear for the next unblocked ticket in the current phase:
   ```
   linear_list_issues(filter: { labels: { name: { eq: "phase-2" } } }, first: 30)
   ```
2. Filter results to Backlog (`state.type: "backlog"`) and not Canceled/Done.
3. Check each ticket's `depends on` chain — all must be Done.
4. Pick the **first unblocked ticket** by phase sequence (e.g. P2.1b before P2.3b).

---

## 2.  Dispatch to -dev Agent

1. Move ticket to **In Progress** and assign:
   ```
   linear_update_issue(issue: "ODY-NN", stateId: "<in-progress-id>", assigneeId: "<self>")
   ```
2. Post a progress comment: `linear_create_comment(issueId: "...", body: "🚀 Scrum master: picking up...")`
3. Classify the work:
   - **Backend** (Python, models, routes, infra, tests) → `backend-dev`
   - **Frontend** (React, UI, a11y, components) → `frontend-dev`
4. Create branch: `git checkout dev2 && git pull origin dev2 && git checkout -b <branch>`
5. Launch the agent:
   ```
   subagent(agent: "backend-dev", output: "ody-NN-implementation.md", task: "<full ticket description>")
   ```

### Backend-dev task template
```
Implement ODY-NN on branch jesserglacken/ody-NN-<slug>. Base: dev2.

[Paste full ticket description with work items and exit criteria]

Conventional commits. Run tests + lint before marking done. Report results.
```

### Frontend-dev task template
```
Implement ODY-NN on branch jesserglacken/ody-NN-<slug>. Base: dev2.

[Paste full ticket description]

WCAG 2.2 AA. Semantic HTML/ARIA. i18n layer. No hard-coded strings.
axe = 0, Lighthouse a11y = 100. Conventional commits. Report results.
```

---

## 3.  Monitor & Assist the -dev Agent

1. `subagent_wait(id: "<run-id>", timeoutMs: 600000)`
2. If the agent detaches for intercom (tool limitations, missing files, questions):
   - Reply via `subagent_supervisor(action: "reply", replyTo: "...", message: "...")`
   - Common issues: wrong branch (switch to dev2), missing files (provide paths), no bash (run shell yourself)
3. If agent fails, inspect `subagent(action: "status", id: "<id>")` for the output artifact.
4. If agent succeeds, proceed to review.

---

## 4.  Pre-Review Validation (scrum master)

Before handing to adversarial-reviewer, verify:

1. `uv run pytest tests/<relevant> -q` — tests pass
2. `uv run ruff check src/ core/ routes/ services/ --select F401,E` — no new lint errors
3. `PYTHONPATH=src uv run python -c "from <module> import <key-class>"` — imports work
4. `git diff dev2 --stat` — scope matches ticket
5. Any missing re-exports, broken backward compat, circular imports?

Fix any issues found **before** handing to the reviewer.

---

## 5.  Adversarial Review Loop

1. Create the PR if not already done:
   ```
   git push -u origin <branch>
   gh pr create --repo jesseGlacken/odysseus --base dev2 --head <branch> \
     --title "type(scope): description (ODY-NN)" --body "<template>"
   ```
2. Launch adversarial-reviewer:
   ```
   subagent(agent: "adversarial-reviewer", output: "ody-NN-review.md",
     task: "Review PR #NN on repo jesseGlacken/odysseus (base: dev2). ...")
   ```
3. Wait for review: `subagent_wait(id: "<id>", timeoutMs: 600000)`
4. Read the review output.  **For every BLOCKER or HIGH finding:**
   a. Fix the code directly in the working directory
   b. `git add` + `git commit --amend --no-edit`
   c. `git push --force-with-lease origin <branch>`
   d. Post resolution comment: `gh pr comment NN --repo jesseGlacken/odysseus --body "✅ Fixed: ..."`
5. Repeat step 4 until all BLOCKER/HIGH findings are resolved.
6. For MEDIUM findings: fix if quick, otherwise document as follow-up.
7. For LOW findings: note and defer.

---

## 6.  CI & Bot Comments

1. After the review loop is done, check CI state:
   ```
   gh pr view NN --repo jesseGlacken/odysseus --json statusCheckRollup
   ```
2. **PR description check**: The `pr-description-check-bot` requires a specific template.
   Always use this structure:
   ```
   ## Summary
   [One paragraph]

   ## Target branch
   - [x] This PR targets **`dev2`**

   ## Linked Issue
   Closes ODY-NN

   ## Type of Change
   - [x] [type]

   ## Checklist
   - [x] I searched open issues and PRs — not a duplicate
   - [x] This PR targets `dev2`
   - [x] [other items]

   ## How to Test
   1. [step]
   2. [step]
   ```
3. **Pytest INTERNALERROR** on `from tests._taxonomy import discover_markers`: pre-existing conftest issue. Not a new failure.
4. **Trivy image scan (advisory)**: advisory, not blocking.
5. If bot requests changes, apply them and push.
6. Verify bot comment auto-deletes when all sections are complete.

---

## 7.  Handoff to User

Post a summary table and prompt:

```
## Pipeline Status — Ready for Review

| Ticket | PR | State |
|--------|-----|-------|
| ODY-NN | [#NN](url) | ✅ Ready |

Ready for your review.
```

---

## Agent Reference

| Agent | Use for |
|-------|---------|
| `backend-dev` | Python, SQLAlchemy, FastAPI routes, tests, infra |
| `frontend-dev` | React components, UI, a11y, i18n |
| `adversarial-reviewer` | Security, ADR compliance, code quality audit |
| `scout` | Fast codebase scanning (no API tokens) |
| `qa-engineer` | Test suites (pytest, Vitest, Playwright) |

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Agent says "no bash" | Subagent tool config | Run shell commands from scrum master context |
| `gh pr create` says "No commits between dev2 and branch" | Remote dev2 advanced | `git fetch origin dev2 && git rebase origin/dev2 && git push --force-with-lease` |
| Circular import in model files | Model files import from `core.database` | Change to `from core.base import ...` |
| `uv.lock` merge conflict | Stash pop conflict | `git checkout -- apps/api/uv.lock && git stash pop` |
| Pytest `INTERNALERROR` in CI | conftest `_taxonomy` import | Pre-existing — not a new failure |
