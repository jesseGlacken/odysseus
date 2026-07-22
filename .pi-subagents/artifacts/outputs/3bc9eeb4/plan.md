# Backend Gap Analysis: Existing Tickets vs. Production Readiness

**Analysis Date:** 2025-07-22  
**Analyzed by:** Planning subagent with backend context  
**Baseline:** dev @ bda7f40  
**Scope:** Assess whether P0.1-P0.7, P1.1-P1.4, P2.1-P2.5 tickets produce a production-ready backend

---

## Executive Summary

The existing 20 backend tickets (ODY-6 through ODY-24) cover **~60%** of what's needed for a production-ready v2 backend. Critical gaps exist in:

1. **SSE/streaming endpoints** (13+ endpoints not covered by P1.3* typed response models)
2. **Test infrastructure** (3,984 mocks vs 366 HTTP tests — no migration strategy)
3. **Middleware & lifecycle hooks** (7 middleware, startup tasks not tested)
4. **Background job system** (50+ asyncio tasks, task_scheduler not covered)
5. **Database migrations** (50+ inline migrations in core/database.py not tested)
6. **services/ directory** (10 service modules not covered)
7. **Coverage target mismatch** (tickets say 80-90%, ADR-0004 requires 100%)
8. **Drop-in replacement verification** (876 frontend fetch() calls not validated)

**Verdict:** The existing tickets will produce a **structurally sound but functionally incomplete** backend. Additional tickets are required to ensure:
- All 483 endpoints work as drop-in replacements
- Tests are meaningful (black-box, not mock-heavy)
- Coverage reaches 100% (not 80-90%)
- Streaming, WebSocket, and background job functionality is preserved

---

## Detailed Gap Analysis

### Gap 1: SSE/Streaming Endpoints Not Covered by P1.3*

**What's missing:**
- 13+ endpoints return `StreamingResponse` with `text/event-stream`
- These cannot have traditional `response_model` (they stream, not return JSON)
- P1.3a-P1.3e (typed response models) don't address streaming endpoints

**Affected endpoints:**
```
routes/chat_routes.py:      4 SSE endpoints (chat_stream, chat_resume, rewrite_message, etc.)
routes/codex_routes.py:     2 SSE endpoints (zip downloads)
routes/model_routes.py:     3 SSE endpoints (model streaming)
routes/shell_routes.py:     3 SSE endpoints (shell output streaming)
routes/research_routes.py:  1 SSE endpoint (research streaming)
routes/email_routes.py:     1 SSE endpoint (email streaming)
```

**Why it matters:**
- Streaming is core to chat functionality (users see tokens appear in real-time)
- OpenAPI schema cannot type a stream — needs special handling
- Black-box testing streaming endpoints requires different patterns (consume stream, validate events)

**Recommendation:**
- **New ticket P1.3f**: Document and test SSE/streaming endpoints
- Scope: Add OpenAPI documentation for streaming endpoints, write black-box tests that consume streams
- Dependencies: P1.1 (contracts package)
- Priority: High (chat is pilot domain)

---

### Gap 2: WebSocket Endpoints Not Covered

**What's missing:**
- chat_routes.py line 364 mentions "websocket reconnect"
- No ticket covers WebSocket endpoint discovery, documentation, or testing
- WebSocket testing requires different patterns than HTTP

**Recommendation:**
- **Expand P1.3b** (Chat domain) to include WebSocket endpoints
- Scope: Find all WebSocket endpoints, document in OpenAPI (if supported), write black-box WebSocket tests
- Priority: Medium (verify if WebSockets are actually used)

---

### Gap 3: Middleware Stack Not Tested

**What's missing:**
- 7 middleware layers in app.py:
  1. `CORSMiddleware` (line 130)
  2. `GZipMiddleware` (line 156)
  3. `SecurityHeadersMiddleware` (line 159)
  4. `_RequestTimeoutMiddleware` (line 242)
  5. `_InteractiveActivityMiddleware` (line 243)
  6. `_SlowRequestLogMiddleware` (line 244)
  7. `AuthMiddleware` (line 471, conditional)

- No ticket covers middleware testing or migration
- Middleware affects ALL endpoints (security headers, timeouts, auth)

**Why it matters:**
- Security middleware is critical (XSS, CSRF, CORS protection)
- Auth middleware gates all authenticated endpoints
- Timeout middleware prevents resource exhaustion

**Recommendation:**
- **New ticket P2.6**: Test and document middleware stack
- Scope: Write black-box tests for each middleware (CORS headers, security headers, timeout behavior, auth enforcement)
- Dependencies: P1.1 (contracts package)
- Priority: High (security-critical)

---

### Gap 4: Lifespan/Startup Hooks Not Tested

**What's missing:**
- app.py `_lifespan` (line 997) runs critical startup tasks:
  1. Incognito session purge (line 1015)
  2. Upload cleanup task (line 1040)
  3. Background job monitor (line 1046)
  4. MCP server connections (line 1054)
  5. Tool index warmup (line 1073, opt-in)
  6. Endpoint warmup (line 1082, opt-in)

- No ticket covers testing startup/shutdown behavior
- These tasks are fire-and-forget (`asyncio.create_task`) — hard to test

**Why it matters:**
- Startup tasks initialize critical subsystems (MCP, background jobs)
- If startup fails silently, features break without error messages
- Shutdown hooks clean up resources (prevent leaks)

**Recommendation:**
- **Expand P0.2** (Relocate backend) to include startup smoke tests
- Scope: Write tests that boot the app and verify startup tasks complete
- Priority: Medium (startup is already working in v1)

---

### Gap 5: Background Job System Not Covered

**What's missing:**
- 50+ `asyncio.create_task` calls across src/
- `src/task_scheduler.py` (2,627 LOC) implements complex scheduled job system
- `src/bg_monitor.py` monitors background bash jobs and re-invokes agent
- `src/agent_runs.py` manages streaming agent tasks
- No ticket covers testing/migrating background job infrastructure

**Why it matters:**
- Task scheduler runs cron jobs, chained tasks, background executions
- Background bash jobs (#!bg) trigger agent continuation when complete
- If these break silently, scheduled tasks and background jobs fail

**Recommendation:**
- **New ticket P2.6**: Test background job system
- Scope: Write black-box tests for task scheduler (create task, execute, verify), bg_monitor (trigger bg job, verify continuation)
- Dependencies: P2.1 (decompose agent_loop), P2.2 (regroup src/)
- Priority: High (task scheduler is 2,627 LOC God module)

---

### Gap 6: services/ Directory Not Covered

**What's missing:**
- `services/` contains 10 service modules:
  - `docs/` (document search/RAG service)
  - `faces/` (face detection)
  - `hwfit/` (hardware fit profiling)
  - `memory/` (memory service)
  - `research/` (research service)
  - `search/` (web search service)
  - `shell/` (shell execution service)
  - `stt/` (speech-to-text service)
  - `tts/` (text-to-speech service)
  - `youtube/` (YouTube transcript extraction)

- P2.2 (Regroup src/) only covers src/, not services/
- Services are imported by routes/ and src/ but not tested in isolation

**Why it matters:**
- Services encapsulate complex domain logic (search ranking, TTS pipeline, YouTube extraction)
- If services break, features fail silently
- Services should be testable in isolation (unit tests)

**Recommendation:**
- **Expand P2.2** (Regroup src/) to include services/
- Scope: Move services/ into src/domain/ or src/services/, write unit tests for each service
- Priority: Medium (services are already working in v1)

---

### Gap 7: Database Migrations Not Tested

**What's missing:**
- `core/database.py` contains 50+ inline migrations:
  - `last_message_at` column (line 819)
  - `documents.archived` column (line 842)
  - `model_endpoints` columns (lines 890, 944, 969, 993, 1021)
  - `task_runs` columns (line 1044)
  - `supports_tools` column (line 1067)
  - `cached_models`, `pinned_models` columns (lines 1090, 1113)
  - `notes` table (line 1145)
  - Email OAuth columns (line 1569)
  - Calendar columns (lines 2259, 2286, 2312, 2342, 2364, 2386)
  - ... and 30+ more

- Migrations run at startup via `init_db()` (line 1893)
- No ticket covers testing migration safety
- P2.5 (Split database) doesn't address migration testing

**Why it matters:**
- Migrations modify production data (backfill columns, encrypt secrets)
- If a migration fails, data is corrupted or lost
- Migrations must be idempotent (safe to run multiple times)

**Recommendation:**
- **New ticket P2.7**: Test database migrations
- Scope: Write tests that verify each migration is idempotent, preserves data, handles edge cases
- Dependencies: P2.5 (split database)
- Priority: High (data loss risk)

---

### Gap 8: Companion Module Missing

**What's missing:**
- app.py line 862: `from companion import setup_companion_routes`
- Cannot find `companion.py` in repo
- Either:
  - It's in a subdirectory (need to locate)
  - It's generated at runtime
  - It's a typo/bug

**Recommendation:**
- **Action item**: Locate companion module and add to ticket scope
- If it's a route file, add to P1.3e (remaining domains)
- If it's a service, add to P2.2 (regroup src/)

---

### Gap 9: Request Models Exist But Aren't Used

**What's missing:**
- `src/request_models.py` contains 10 Pydantic models:
  - `ChatRequest`, `SessionCreateRequest`, `MemoryAddRequest`, `MemoryUpdateRequest`
  - `PresetUpdateRequest`, `DirectoryRequest`
  - `ErrorResponse`, `UploadResponse`, `SessionResponse`, `MemoryResponse`

- Only 3 endpoints use `response_model`
- P1.3* tickets don't mention using existing `request_models.py`

**Recommendation:**
- **Expand P1.3a-P1.3e** to use existing `request_models.py` as starting point
- Scope: Review existing models, extend as needed, apply to endpoints
- Priority: Low (convenience improvement)

---

### Gap 10: Test Infrastructure Is Broken

**What's missing:**
- `tests/conftest.py` stubs out critical modules at MODULE SCOPE:
  ```python
  for mod_name in ["sqlalchemy", "sqlalchemy.orm", ...]:
      if mod_name not in sys.modules and not _has_module(mod_name):
          sys.modules[mod_name] = MagicMock()
  ```
- Tests import stubs that replace `core.database`, `sqlalchemy` with MagicMock
- 3,984 mock.patch calls vs 366 HTTP TestClient calls
- No ticket covers fixing test infrastructure

**Why it matters:**
- Mock-heavy tests violate ADR-0004 (black-box testing mandate)
- Tests that stub core.database can't catch real database bugs
- P1.4 (flip gates) assumes tests are meaningful, but they're not

**Recommendation:**
- **New ticket P1.5**: Migrate test suite to black-box pattern
- Scope:
  1. Triage existing tests (keep/convert/delete)
  2. Fix conftest.py to use real database (test container or in-memory SQLite)
  3. Convert mock-heavy tests to HTTP TestClient pattern
  4. Write Gherkin .feature files for core domains
- Dependencies: P1.1 (contracts package), P0.4 (CI gates)
- Priority: Critical (blocks P1.4 gate flip)

---

### Gap 11: Coverage Target Mismatch

**What's missing:**
- P1.4 says "Coverage ≥ 80%"
- P2 says "Coverage ≥ 90%"
- ADR-0004 requires **100% line AND branch coverage**
- No ticket covers the final push from 90% to 100%

**Why it matters:**
- ADR-0004 is a non-negotiable (traces to CI gate)
- 90% coverage means 10% of code is untested (dead code or missing tests)
- ADR-0004 rule 7: "Dead code is deleted, not excused"

**Recommendation:**
- **New ticket P2.8**: Achieve 100% coverage
- Scope:
  1. Run coverage report, identify gaps
  2. Write tests for uncovered code OR delete dead code
  3. Verify `knip`/`vulture` clean
- Dependencies: P2.1-P2.7 (all backend work)
- Priority: High (blocks v2.0 release)

---

### Gap 12: Black-Box Testing Strategy Missing

**What's missing:**
- 3,984 mocks vs 366 HTTP tests
- P1.3* tickets say "write Gherkin scenarios" but don't address converting existing tests
- No ticket covers the migration from mock-based to black-box testing

**Why it matters:**
- ADR-0004 rule 3: "Test through public surfaces: HTTP endpoints on the backend"
- ADR-0004 rule 3: "Never mock internal collaborators to manufacture coverage"
- Existing tests violate both rules

**Recommendation:**
- **Expand P1.5** (from Gap 10) to include black-box conversion strategy
- Scope:
  1. Identify tests that mock internal collaborators
  2. Convert to HTTP TestClient pattern (test through endpoints)
  3. Delete tests that can't be converted (if they test implementation detail)
- Priority: Critical (blocks ADR-0004 compliance)

---

### Gap 13: Mutation Testing Not Operationalized

**What's missing:**
- ADR-0004 rule 6: "Mutation tests must pass"
- P0.4 (CI gates) says "advisory" but doesn't specify mutation tool
- No ticket covers setting up mutation testing infrastructure

**Why it matters:**
- Mutation testing catches weak tests (tests that pass even when code is wrong)
- ADR-0004 rule 6: "When mutants survive, add real assertions — do not annotate them away"

**Recommendation:**
- **Expand P0.4** (CI gates) to include mutation testing setup
- Scope:
  1. Install mutation tool (mutmut for Python, stryker for JS)
  2. Configure mutation testing in CI (advisory first, then blocking)
  3. Run mutation tests on pilot domain (auth)
- Dependencies: P1.3a (auth domain clean)
- Priority: Medium (mutation testing is advanced quality gate)

---

### Gap 14: Existing Test Suite Needs Triage

**What's missing:**
- 81,577 LOC, 3,248 test functions
- Many are mock-heavy and violate ADR-0004
- No ticket covers triaging which tests to keep, convert, or delete

**Why it matters:**
- Risk: deleting tests lowers coverage
- Risk: keeping bad tests violates ADR-0004
- Need clear criteria for keep/convert/delete

**Recommendation:**
- **Expand P1.5** (from Gap 10) to include test triage
- Scope:
  1. Categorize tests: black-box (keep), mock-heavy (convert), implementation detail (delete)
  2. Prioritize conversion of high-value tests (security, core domains)
  3. Delete tests that test private functions or implementation detail
- Priority: High (blocks P1.4 gate flip)

---

### Gap 15: Drop-In Replacement Compatibility Not Verified

**What's missing:**
- Frontend has 876 raw `fetch()` calls to API routes
- New backend must maintain exact URL paths, query params, response shapes
- No ticket covers endpoint compatibility verification
- No ticket covers regression testing against real frontend

**Why it matters:**
- If endpoint URLs change, frontend breaks
- If response shapes change, frontend breaks
- Strangler pattern requires v2 to be drop-in replacement before cutover

**Recommendation:**
- **New ticket P1.6**: Verify drop-in replacement compatibility
- Scope:
  1. Extract all 876 frontend fetch() calls (URLs, methods, expected responses)
  2. Write black-box tests that verify v2 endpoints match v1 behavior
  3. Run frontend against v2 backend, verify no errors
- Dependencies: P1.3a-P1.3e (typed response models)
- Priority: High (blocks v2.0 cutover)

---

## Summary of Recommended New/Expanded Tickets

| Gap | Ticket | Type | Priority | Dependencies |
|-----|--------|------|----------|--------------|
| 1 | **P1.3f**: Document and test SSE/streaming endpoints | New | High | P1.1 |
| 2 | **P1.3b** (expand): Include WebSocket endpoints | Expand | Medium | P1.1 |
| 3 | **P2.6**: Test and document middleware stack | New | High | P1.1 |
| 4 | **P0.2** (expand): Include startup smoke tests | Expand | Medium | None |
| 5 | **P2.7**: Test background job system | New | High | P2.1, P2.2 |
| 6 | **P2.2** (expand): Include services/ directory | Expand | Medium | None |
| 7 | **P2.8**: Test database migrations | New | High | P2.5 |
| 8 | **Action item**: Locate companion module | Action | Low | None |
| 9 | **P1.3a-P1.3e** (expand): Use existing request_models.py | Expand | Low | None |
| 10 | **P1.5**: Migrate test suite to black-box pattern | New | Critical | P1.1, P0.4 |
| 11 | **P2.9**: Achieve 100% coverage | New | High | P2.1-P2.8 |
| 12 | **P1.5** (expand): Include black-box conversion strategy | Expand | Critical | P1.1 |
| 13 | **P0.4** (expand): Include mutation testing setup | Expand | Medium | P1.3a |
| 14 | **P1.5** (expand): Include test triage | Expand | High | None |
| 15 | **P1.6**: Verify drop-in replacement compatibility | New | High | P1.3a-P1.3e |

---

## Revised Backend Ticket List

### Phase 0: Foundation (existing + expansions)
- P0.1 (ODY-7): Initialize Nx Workspace ✓
- P0.2 (ODY-6): Relocate Backend into apps/api/ ✓ **+ startup smoke tests**
- P0.3 (ODY-8): Create packages/config/ ✓
- P0.4 (ODY-10): Scaffold Advisory CI Gates ✓ **+ mutation testing setup**
- P0.5 (ODY-11): Remove Test Deps from Runtime ✓
- P0.7 (ODY-9): Integrate OTel Skeleton ✓

### Phase 1: Contract-First (existing + new)
- P1.1 (ODY-12): Create packages/contracts/ ✓
- P1.2 (ODY-17): Create packages/client-sdk/ ✓
- P1.3a (ODY-16): Typed Response Models — Auth Domain ✓ **+ use request_models.py**
- P1.3b (ODY-13): Typed Response Models — Chat Domain ✓ **+ WebSocket endpoints**
- P1.3c (ODY-15): Typed Response Models — Documents Domain ✓ **+ use request_models.py**
- P1.3d (ODY-14): Typed Response Models — Email Domain ✓ **+ use request_models.py**
- P1.3e (ODY-23): Typed Response Models — Remaining Domains ✓ **+ use request_models.py**
- **P1.3f (NEW)**: Document and test SSE/streaming endpoints
- P1.4 (ODY-24): Flip Quality Gates to Blocking ✓
- **P1.5 (NEW)**: Migrate test suite to black-box pattern (triage, convert, Gherkin)
- **P1.6 (NEW)**: Verify drop-in replacement compatibility (876 fetch() calls)

### Phase 2: Backend Decoupling (existing + new)
- P2.1 (ODY-18): Decompose stream_agent_loop ✓
- P2.2 (ODY-19): Regroup src/ into Domain Packages ✓ **+ include services/**
- P2.3 (ODY-20): Introduce Repository Layer ✓
- P2.4 (ODY-22): Remove src→routes Backward Imports ✓
- P2.5 (ODY-21): Split core/database.py ✓
- **P2.6 (NEW)**: Test and document middleware stack
- **P2.7 (NEW)**: Test background job system
- **P2.8 (NEW)**: Test database migrations
- **P2.9 (NEW)**: Achieve 100% coverage

---

## Critical Path

```
P0.1 → P0.2 → P0.4 → P1.1 → P1.3a → P1.5 (test migration) → P1.4 (flip gates)
                                    ↓
                              P1.3b-P1.3e (typed models)
                                    ↓
                              P1.3f (streaming) → P1.6 (drop-in verification)
                                    ↓
                              P2.1 → P2.2 → P2.3 → P2.4 → P2.5
                                                              ↓
                                                        P2.6-P2.8 (testing)
                                                              ↓
                                                        P2.9 (100% coverage)
```

**Critical path length:** 14 tickets (P0.1 → P2.9)  
**Parallelizable:** P1.3a-P1.3e, P2.6-P2.8

---

## Risks

### High Risks
1. **Test migration is harder than expected**
   - 3,984 mocks to convert
   - Risk: takes 2-3x longer than estimated
   - Mitigation: Start with pilot domain (auth), learn, then scale

2. **Streaming endpoints can't be typed**
   - OpenAPI doesn't support typing streams
   - Risk: P1.3f blocked by tooling limitations
   - Mitigation: Document streams manually, write black-box tests that consume streams

3. **Database migrations are fragile**
   - 50+ inline migrations, some modify production data
   - Risk: migration tests reveal bugs, delay P2.8
   - Mitigation: Review migrations carefully, fix bugs before testing

### Medium Risks
1. **Background job system is complex**
   - task_scheduler.py is 2,627 LOC God module
   - Risk: P2.7 reveals hidden bugs
   - Mitigation: Decompose task_scheduler before testing (add to P2.1 scope)

2. **Drop-in replacement verification is incomplete**
   - 876 fetch() calls, some may use undocumented behavior
   - Risk: P1.6 reveals edge cases
   - Mitigation: Run real frontend against v2 backend, fix issues iteratively

3. **Coverage target is unrealistic**
   - 100% coverage from 47.5% is aggressive
   - Risk: P2.9 takes too long
   - Mitigation: Delete dead code aggressively, focus on reachable code

---

## Conclusion

The existing 20 backend tickets provide a **solid structural foundation** but are **functionally incomplete** for production readiness. The 9 new/expanded tickets address critical gaps in:

1. **Testing infrastructure** (P1.5: black-box migration, P2.9: 100% coverage)
2. **Streaming/WebSocket support** (P1.3f: SSE endpoints, P1.3b expansion)
3. **Infrastructure testing** (P2.6: middleware, P2.7: background jobs, P2.8: migrations)
4. **Compatibility verification** (P1.6: drop-in replacement)

**Final verdict:** With the 9 additional tickets, the backend will be:
- ✓ Structurally sound (Nx monorepo, typed contracts, decomposed modules)
- ✓ Functionally complete (all 483 endpoints work, streaming preserved)
- ✓ Thoroughly tested (black-box, 100% coverage, mutation tested)
- ✓ Drop-in compatible (876 frontend fetch() calls validated)

**Recommendation:** Approve the 9 new/expanded tickets and add them to the Linear project with proper dependency linkages.
