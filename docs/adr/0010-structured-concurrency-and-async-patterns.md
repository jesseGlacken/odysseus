# ADR-0010: Structured concurrency & async patterns

- **Status:** Accepted
- **Date:** 2026-07-22
- **Deciders:** Repository owner
- **Supersedes:** none
- **Superseded by:** none

## Context

The v1 backend has 50+ `asyncio.create_task()` calls across `app.py` (startup tasks),
`src/builtin_actions.py` (email summarisation, skill tests), `src/email_pollers.py` (IMAP
polling), `src/cookbook_*.py` (model download/serve lifecycle), and `src/agent_runs.py`
(streaming agent execution). These are fire-and-forget — errors in background tasks are
logged but not recovered, tasks have no lifecycle visibility, and cancellation during
shutdown is ad-hoc.

Python 3.11 introduced `asyncio.TaskGroup` for structured concurrency, mirroring the
pattern established by Trio and adopted by the broader async Python ecosystem.

The v2 refactor of `src/agent_loop.py` (CC 531 → submodules) and `src/` regrouping
(Phase 2) presents the right moment to standardise async patterns.

## Decision

1. **`asyncio.TaskGroup` is the default for spawning concurrent tasks.** `create_task()`
   is permitted only for fire-and-forget tasks whose failure MUST NOT propagate to the
   caller (e.g., non-critical metrics emission, cache warming). All task groups use
   `async with` to ensure cleanup on scope exit.

2. **Every async task must have defined lifecycle management:**
   - **Creation:** Task is spawned with a descriptive name (`name=` parameter for
     `create_task` or via TaskGroup context).
   - **Cancellation:** Task handles `asyncio.CancelledError` in a `try/finally` block
     to clean up resources (close connections, flush buffers, release locks).
   - **Error handling:** Task exceptions are logged with traceback context. Tasks that
     represent critical workflows (agent execution, email polling) propagate errors to
     the parent scope via TaskGroup's exception group.
   - **Timeout:** Long-running tasks specify a timeout via `asyncio.wait_for()` or
     `asyncio.timeout()` context manager. Defaults: 30s for HTTP-bound tasks, 300s for
     agent execution, 600s for model download/serve.

3. **Streaming tasks (SSE, agent output) use `asyncio.Queue` as the standard
   producer-consumer channel.** The producer writes to the queue; the consumer reads
   and sends SSE events. Queue size is bounded (default 256 items) to provide
   backpressure — a full queue signals the producer to pause.

4. **Startup tasks in `app.py` `_lifespan` use `TaskGroup` for parallel initialisation.**
   Each startup task (incognito purge, upload cleanup, MCP connections, tool index
   warmup) is spawned in a TaskGroup. If a critical startup task fails, the application
   fails to start. If a non-critical task fails, the application starts with a warning
   log.

5. **Background polling uses `asyncio.Task` with explicit start/stop control:**
   - Polling tasks (IMAP, CalDAV, task scheduler) expose `start()` and `stop()` methods.
   - `stop()` sets a cancellation event and awaits the task.
   - Shutdown (`_lifespan` exit) calls `stop()` on all polling tasks and awaits
     completion within a 10-second grace period before force-cancelling.

6. **The task scheduler (`src/task_scheduler.py`) is refactored to use structured
   concurrency during Phase 2.** Currently 2,627 LOC with CC 50+ functions — it is
   a candidate for decomposition with TaskGroup-based execution.

## Consequences

- **Positive:** deterministic task lifecycle; errors surface predictably; shutdown is
  graceful; backpressure prevents memory exhaustion on busy streams.
- **Negative / costs:** migrating 50+ existing `create_task()` calls to TaskGroup
  patterns is effort; developers must learn structured concurrency patterns;
  `CancelledError` handling must be thorough or tasks leak resources.
- **Enforcement:** Code review of async code must verify TaskGroup usage, cancellation
  handling, and timeout configuration. A custom AST lint (or ruff rule in future) can
  flag bare `create_task()` outside approved patterns.

## Alternatives considered

- **Continue with ad-hoc `create_task()` (v1 style).** Rejected: unstructured
  concurrency is the cause of silent failures, shutdown hangs, and unobservable
  background task states in v1. Structured concurrency is a Python 3.11 stdlib
  feature — there is no cost to adopting it.
- **Use Trio or AnyIO instead of asyncio.** Rejected: FastAPI and the existing
  ecosystem are asyncio-native. Introducing an alternative event loop adds
  complexity without proportional benefit.
- **Use `concurrent.futures` for CPU-bound work only.** Accepted as complementary:
  `run_in_executor()` for CPU-bound parsing, image processing, or encryption.
  I/O-bound work stays on the asyncio event loop.
