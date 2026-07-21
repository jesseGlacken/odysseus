# Odysseus — Architectural Review

> Baseline: working tree `dev @ bda7f40` · Reviewed 2026-07-21. Every quantitative claim is
> reproducible from the commands in [Methodology](#methodology) (radon, an import scan, and a live
> `pytest --cov` run).

**Verdict:** a capable, feature-dense app with genuinely strong security/CI hygiene and a large test
suite — carrying real architectural debt concentrated in a handful of oversized modules, plus a front
end with **zero** automated tests.

## Scorecard

Grades are relative to what a well-run project of this size and ambition should look like, not pass/fail.

| Dimension | Grade | Note |
|---|---|---|
| Backend architecture | C+ | Clear layered intent; flat `src/`, God modules |
| Frontend architecture | C− | Modular ESM, but 11k-line files & no tooling |
| Coupling | C | DB hub; 36 backward `src→routes` imports |
| Cyclomatic complexity | C | Avg fine; 53 F-grade blocks, one at 531 |
| Backend test coverage | C+ | 47.5% lines; routes tier only 36% |
| Frontend test coverage | F | 0 automated tests across ~133k JS LOC |
| Test pyramid | C | Wide unit base; no E2E/UI tier |
| SOLID adherence | C− | SRP & DIP are the weak spots |
| Docs ↔ code accuracy | C | Architecture spec already stale |
| Security / CI posture | A− | Trivy, gitleaks, zizmor, SSRF tests, 2FA |

**Genuinely good:** serious supply-chain/container security in CI; a real testing culture (4,678
tests, marker taxonomy, fast lane, Antithesis fuzzing); layering *intent* is present and refactors
are already in flight; security-sensitive code (auth, SSRF/URL safety, prompt-injection, redaction)
is explicitly modelled and tested.

**Needs attention first:** a ~133k-LOC front end with **zero** tests and no lint/types;
`stream_agent_loop` at cyclomatic complexity **531** and 14 core files at the maintainability floor;
36 backward `src → routes` imports; test-only packages (`pytest`, `httpx2`) shipped as **runtime**
dependencies.

## System context & stack

A single-process FastAPI monolith serving a static, framework-free browser front end, backed by
SQLite and local AI subsystems (vector store, embeddings, local model serving, IMAP/CalDAV bridges).

| Concern | Choice | Notes |
|---|---|---|
| Language / runtime | Python 3.11 | Single Uvicorn process |
| Web framework | FastAPI + Starlette | SSE streaming for chat/agent |
| Data / ORM | SQLAlchemy → SQLite | All models in one 2,562-line module |
| Validation | Pydantic v2 | Settings via pydantic-settings |
| AI / RAG | chromadb-client · fastembed | Keyword fallback if unavailable |
| Frontend | Vanilla ES modules | No framework, bundler, or transpiler |
| Styling | One hand-written CSS file | 40,453 lines |
| Packaging | Docker + PyInstaller | Native macOS/Windows build scripts |
| Tests | pytest + pytest-asyncio | Antithesis/bombadil fuzzing dev-dep |

## Backend architecture

The intended layering is sound and legible. The problems are structural mass: a flat 139-file `src/`
with no domain grouping, and a dozen modules grown past the point of safe review.

| Layer | Files | LOC | Role & health |
|---|---:|---:|---|
| `app.py` | 1 | 1,281 | Entrypoint / router registration — reasonable |
| `core/` | 11 | 4,855 | Infra: auth, session, middleware, DB — `database.py` oversized |
| `routes/` | 67 | 43,699 | HTTP handlers — partially sub-packaged; some files >3k lines |
| `src/` | 139 | 53,814 | Domain / agent / tools — flat, no grouping |
| `services/` | 40 | 10,055 | hwfit · memory · search · tts/stt — well-foldered |
| `mcp_servers/` | 5 | 3,162 | Separate MCP processes — lower risk |
| `integrations/` | 2 | 436 | Small; highest *average* complexity (D) |

**Heaviest modules** (`src/agent_loop.py` — not `tool_implementations.py` as the internal spec still
claims — is now the largest and most complex):

| Module | LOC | MI rank | Why it's risky |
|---|---:|---|---|
| `src/agent_loop.py` | 4,529 | MI 0.0 | `stream_agent_loop` (CC 531) + `_build_system_prompt` (CC 115) |
| `routes/email_routes.py` | 5,226 | MI 0.0 | Largest route module; email is the most complex domain |
| `routes/cookbook_routes.py` | 4,386 | C | Model download/serve orchestration; 11% covered |
| `src/llm_core.py` | 2,869 | MI 0.0 | `_stream_llm_inner` (CC 216); 34 importers |
| `src/builtin_actions.py` | 2,776 | MI 0.0 | Source of most `src→routes` backward imports |
| `src/task_scheduler.py` | 2,627 | MI 0.0 | Two F-grade methods; cron/reminder engine |
| `core/database.py` | 2,562 | MI 0.0 | 28 models + ~59 helpers; 56-file fan-in hub |

> Maintainability Index (radon `mi`): 0–100, higher is better; 0.0 is the reporting floor these files
> all hit. 227 of 263 files rank healthy (A) — the debt is concentrated in ~20 mega-modules.

The flat `src/` is the root organizational problem: 139 modules in one directory with no `domain/`,
`infra/`, or `agent/` grouping, which is what lets modules quietly grow past 2,000 lines.

## Frontend architecture

A deliberately dependency-light, build-free front end: 151 of 153 files are native ES modules loaded
directly by the browser. Simple and honest, but shipped with none of the safety rails a codebase this
size needs.

**Largest JS modules:** `document.js` 11,038 · `emailLibrary.js` 7,784 · `slashCommands.js` 6,513 ·
`settings.js` 5,795 · `chat.js` 5,457 · `notes.js` 5,373 · `app.js` 4,389.

**Third-party surface:** vendored (3.3 MB) — `xlsx` 952 KB, `html2pdf` 906 KB, `docx` 743 KB,
`mammoth` 642 KB, `highlight`, `qrcode`; loaded from CDN — `katex`, `mermaid`, `pdfobject`, and a full
`pyodide` Python runtime (v0.27.5).

- **Critical:** no `.test.js`/`.spec.js`, no Playwright, ESLint, or TypeScript config anywhere. CI runs
  only `node --check` (syntax). ~133k lines of UI logic have no automated regression protection.
- **Performance:** single files reach 11k lines; `index.html` is 228 KB; `style.css` is 40,453 lines
  in one file. No bundling/code-splitting, so first load pulls large un-minified payloads.

## Dependency graph & coupling

Coupling follows the intended direction most of the time. Two things stand out: a strong hub-and-spoke
around `core.database`, and a persistent backward dependency from domain code into HTTP handlers.

| Flow | Imports | Read |
|---|---:|---|
| `routes → src` | 389 | expected |
| `routes → core` | 139 | expected |
| `src → src` | 463 | internal |
| `src → core` | 113 | acceptable |
| `src → routes` | 36 | **violation** |
| `services → src` | 30 | watch |

**Most-imported modules (fan-in, non-test):** `src.constants` 60 · `core.database` 56 ·
`src.auth_helpers` 43 · `src.llm_core` 34 · `core.middleware` 28 · `src.settings` 27.

**Layering violation:** 36 domain→HTTP imports across 13 `src/` files — mostly function-body (inline)
imports to dodge circular-import errors; `src/builtin_actions.py` alone accounts for ~13. Inline
imports keep the app booting but signal that shared logic belongs in `src/`/`services/`, not the route
module it's reached into.

## Cyclomatic complexity

Measured with radon over 2,657 blocks. Average is healthy (**B / 7.66**); the story is the tail: 53
functions grade F and 36 exceed a complexity of 50.

**Grade distribution:** A 1,627 · B 546 · C 314 · D 75 · E 42 · F 53. (CC > 50: 36 blocks; CC > 20: 170.)

**Worst offenders:**

| Function · file | CC |
|---|---:|
| `stream_agent_loop` · agent_loop.py | 531 |
| `_auto_summarize_pass_single` · email_pollers.py | 248 |
| `_stream_llm_inner` · llm_core.py | 216 |
| `do_manage_calendar` · tools/calendar.py | 143 |
| `action_check_email_urgency` · builtin_actions.py | 140 |
| `dispatch_reminder` · note_routes.py | 140 |
| `_build_system_prompt` · agent_loop.py | 115 |

`stream_agent_loop` (CC 531) is the core agent turn-loop as a single function — it cannot be
exhaustively tested, safely modified, or reasoned about in one sitting. It is the highest-value
refactor target, and the internal spec already proposes splitting it into
prompt/classifier/verifier/runaway/context submodules.

## SOLID assessment

| Principle | Grade | Evidence |
|---|---|---|
| **S** — Single responsibility | weak | God modules (`agent_loop`, `database`, `email_routes`) and mega-functions each own many concerns |
| **O** — Open/closed | mixed | Tools/actions dispatched via large `if/elif` and `do_manage_*` switches (CC 60–143) |
| **L** — Liskov substitution | n/a-ish | Little class inheritance on hot paths; mostly module functions |
| **I** — Interface segregation | mixed | Broad multi-purpose entry points bundle many operations behind one function |
| **D** — Dependency inversion | weak | Routes & domain talk to concrete SQLAlchemy directly — no repository/port; 56 modules bind to the concrete store |

Handled well: security concerns *are* separated into focused modules (`url_safety`,
`prompt_security`, `tool_security`, `secret_storage`), and the recent `tool_implementations.py` →
`src/tools/*` split shows the team can execute SRP-restoring refactors.

## Test coverage & pyramid

Volume is a real strength; shape is not. A wide base of mock-heavy unit tests with a thin
HTTP-integration tier and no UI/end-to-end layer.

**Backend coverage (live fast-lane run):** 4,670 passed, 3 skipped, in 2m43s. **47.5% overall**
(29,634 / 62,450 statements).

| Layer | Coverage |
|---|---:|
| `core/` | 72.6% |
| `services/` | 64.1% |
| `src/` | 54.9% |
| `mcp_servers/` | 36.2% |
| `routes/` | 35.6% |
| `app.py` | 0.4% |

**Test-type mix (734 files):** mocks/patching (isolated unit) 356 · touch the DB 138 · async 70 ·
HTTP integration (`TestClient`) 18 · browser/E2E 0 · JavaScript/frontend 0.

The pyramid is intact at the base but truncated at the top: no UI/E2E tier, and the integration waist
is narrow relative to 67 route modules. Despite 4,678 tests, the `routes/` layer is only 35.6% covered
and `app.py` ~0% — the tests concentrate on domain/parser logic, not the HTTP handlers users hit
(`cookbook_routes` 11%, `chat_routes` 9%, `email_routes` 20%). Route-level regressions can slip through
a green suite.

> Coverage caveat: the figure is the **fast lane** (`-m "not slow"`, nearly the whole suite — only 2
> tests are marked slow) run in-container; treat it as ±a couple points, not a certified CI number.

## Docs ↔ implementation drift

Primary architecture doc: `specs/architecture-runtime-inventory.md` (snapshot dev@b58af42, 2026-06-16).
It honestly labels itself a snapshot, but several *structural* claims are now wrong, and refactors it
proposed as "candidates" have quietly shipped.

| Doc claims | Actual | |
|---|---|---|
| `tool_implementations.py` is a 4,032-line monolith (top split candidate) | A **115-line shim**; already split into `src/tools/{calendar,contacts,cookbook,image,notes,research,search,system}.py` | wrong |
| `routes/` = 54 flat files, 0 subdirectories | **67 files, 6 sub-packages** (note, gallery, contacts, history, memory, research) | wrong |
| Config lives in `conf/` (used in a validation command) | **No `conf/` exists**; config is `src/config.py`/`settings.py` — the documented command would fail | wrong |
| Largest module is `tool_implementations.py`; `database.py` 2,265 lines; `app.py` 1,145 | `agent_loop.py` is now largest; `database.py` **2,562**; `app.py` **1,281** | stale |
| Tests: 583 files / ~54,800 lines | **734 files / ~81,500 lines** | stale |
| `src → routes` backward imports: 31 | **36** across 13 files | stale |
| `style.css` 36,653 lines / `document.js` 9,776 | Both larger (40,453 / 11,038); neither frontend slice done | stale |

Because the doc's own recommended refactors have partially landed, a new contributor would target work
that's already done and run validation commands that fail. It needs a scheduled recompute or a shift to
generated-from-source metrics.

## Prioritized improvements

Effort for one experienced engineer: **S** ≤ 1 day, **M** ≈ 2–5 days, **L** ≈ 1–3 weeks, **XL** ≈ 1 month+.

### Critical

| Improvement | Effort | Why |
|---|---|---|
| Frontend test harness (Vitest/Playwright) + smoke E2E for chat, editor, email | L | Closes the largest risk gap: ~133k untested LOC |
| Decompose `stream_agent_loop` (CC 531) into prompt/classifier/verifier/runaway/context | L | Highest-complexity code on the core agent path |
| Break the `src → routes` backward dependency (move shared logic down) | M | Removes 36 layering violations & latent circular imports |
| Remove `pytest`/`pytest-asyncio`/`httpx2` from `requirements.txt` into a dev extra | S | Stops shipping test tooling into production/Docker images |
| Add a JS lint gate (ESLint) alongside `node --check` | S | Cheapest quality win for the untooled front end |

### Quality of life

| Improvement | Effort | Why |
|---|---|---|
| Group flat `src/` into `domain/`/`agent/`/`infra/`/`llm/` packages (re-export shims) | L | Gives extracted code a home; slows module gigantism |
| Split `core/database.py` models by domain (do this **last**, 56 importers) | L | Unblocks a repository layer (fixes DIP) |
| Maintainability gate: fail CI on new blocks > CC 20 (radon) | S | Stops the F-grade tail from growing |
| Add `ruff` + optional `mypy` on `src/`/`core/` | M | No linter/type-checker exists today |
| Split `document.js`/`emailLibrary.js`; modularize `style.css` | L | Editor & email are the biggest single-file UI risks |
| Vendor the CDN assets (katex, mermaid, pyodide) for offline mode | M | Already on the ROADMAP; removes external runtime dependency |
| Add a coverage report to CI & auto-recompute the architecture inventory | S | Makes drift visible; stops docs going stale silently |
| Widen the HTTP-integration tier (18 `TestClient` files for 67 route modules) | M | Thickens the pyramid waist where routes are under-covered |

**Suggested sequence:** land the cheap gates first (dev-deps split, ESLint, radon & coverage in CI) to
freeze the debt; then take the two big correctness gaps in parallel — a frontend smoke-test harness and
the `agent_loop` decomposition; save the `src/` re-grouping and the `database.py` split for last, once
tests give a safety net.

## Methodology

```bash
radon cc app.py core routes src services mcp_servers -s -a        # cyclomatic complexity + grade bands
radon mi app.py core routes src services mcp_servers -s           # maintainability index (0.0 = floor)
grep -rhE '(from|import) +routes' src/ | wc -l                     # src -> routes backward imports (36)
grep -rlE '(from|import) +core\.database' --include=*.py .         # core.database fan-in
python -m pytest --collect-only -q                                # 4,678 tests collected
python -m pytest -m "not slow" --cov=app --cov=core --cov=routes \
       --cov=src --cov=services --cov=mcp_servers                  # 4,670 passed · 2m43s · 47.5% overall
find static/js -name '*.js' | xargs wc -l                         # frontend LOC (no build/test tooling)
```
