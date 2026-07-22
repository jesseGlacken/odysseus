# ADR-0012: Observability & error handling

- **Status:** Accepted
- **Date:** 2026-07-22
- **Deciders:** Repository owner
- **Supersedes:** none
- **Superseded by:** none

## Context

v1 has partial observability: `core/middleware.py` includes security and slow-request
logging; `core/log_safety.py` redacts sensitive data from logs; OTel instrumentation is
skeleton-only (planned for Phase 0.7). The v1 frontend has zero observability — no error
boundaries, no structured client-side logging, no RUM metrics.

v2 migrates to a decoupled frontend-backend architecture where errors can originate in
either runtime and manifest in the other. Without standardised error handling and
observability, debugging cross-boundary failures becomes guesswork.

ADR-0004 mandates 100% test coverage but tests can't cover: production-only failures
(network partitions, disk full, GPU OOM), performance degradation over time, or the
shape of errors users actually see.

Industry standards (OpenTelemetry, Honeycomb, Google SRE Workbook, Twelve-Factor App)
converge on: structured logging, distributed tracing, standardised error taxonomy,
and real-user monitoring.

## Decision

1. **OpenTelemetry is the observability backbone.** Every service boundary (HTTP
   handler, LLM call, tool execution, database query) emits a span. Spans carry
   attributes: `session.id`, `user.id`, `model.name`, `tool.name`, `error.type`
   (when applicable). This is initially opt-in via `OTEL_EXPORTER_OTLP_ENDPOINT`
   (per ADR-0001 Phase 0.7) and is intended to become the default in production.

2. **Frontend Real-User Monitoring (RUM):** The React SPA emits Web Vitals
   (LCP, CLS, TBT, INP) and custom spans for user interactions (chat submit,
   document upload, model selection). All spans carry `session.id` for correlation
   with backend traces.

3. **Structured logging replaces print-style logging.** All log messages:
   - Use Python `logging` with `extra=` dicts (not string interpolation).
   - Include `session_id` and `user_id` when available (or `-` for unauthenticated
     requests).
   - Redact secrets and PII via `core/log_safety.py` before emission.
   - Are emitted as JSON (structured) in production and human-readable in development.

4. **Error taxonomy — every user-visible error maps to one of:**
   | Error Class | HTTP Status | User Message | Retryable |
   |---|---|---|---|
   | `ValidationError` | 422 | Specific field-level message | No (fix input) |
   | `AuthenticationError` | 401 | "Authentication required" | Yes (re-login) |
   | `AuthorizationError` | 403 | "Access denied" | No |
   | `NotFoundError` | 404 | "Resource not found" | No |
   | `TimeoutError` | 504 | "Request timed out" | Yes |
   | `ServiceUnavailableError` | 503 | "Service temporarily unavailable" | Yes |
   | `InternalError` | 500 | "An unexpected error occurred" + request ID | Yes |

   Domain code raises typed exceptions (`ValidationError`, `NotFoundError`, etc.).
   A global exception handler in `app.py` maps them to HTTP responses with
   consistent JSON shapes (`{"error": {"type": "...", "message": "...", "request_id": "..."}}`).
   The `request_id` is a UUID generated on the inbound request and propagated to all
   spans, logs, and the error response — so a user can quote it to support.

5. **Error boundaries in the React SPA:** Every route and every floating panel is
   wrapped in an error boundary. When a boundary catches an error:
   - The error is logged to the console and exported as an OTel span.
   - The user sees an inline error state with a "Retry" button and the request ID.
   - The rest of the application (other routes, sidebar, rail) continues to function.

6. **Alerting thresholds** (defined, not enforced by CI — this is operational):
   - Error rate > 5% of requests over a 5-minute window triggers an alert.
   - 95th percentile latency > 2x baseline triggers an alert.
   - SSE stream disconnect rate > 10% over 5 minutes triggers an alert.
   - Background task failure rate > 0% over 1 hour triggers an alert.

7. **Dashboard minimums:**
   - RED metrics (Rate, Error rate, Duration) per endpoint, per model, per tool.
   - SSE stream active count, lifespan distribution.
   - Database query latency and error rate.
   - Web Vitals histogram per route.

## Consequences

- **Positive:** errors are traceable across FE/BE boundaries; users always see a
  meaningful error message with a correlation ID; operations has alerting thresholds;
  debug time decreases.
- **Negative / costs:** OTel instrumentation adds ~1-5ms per span; structured logging
  increases log volume; error taxonomies must be maintained as the API evolves.
- **Enforcement:** global exception handler (app.py) enforces error shapes; error
  boundary component in `packages/ui` enforces FE error handling; OTel test verifies
  spans are emitted; structured-logging test verifies JSON output format.

## Alternatives considered

- **No centralised error taxonomy — let each handler define its own error shape.**
  Rejected: the v1 frontend's 876 raw `fetch()` calls handle errors with inconsistent
  patterns (some check `status`, some check `.ok`, some just `.catch()`). A typed
  error contract eliminates this inconsistency.
- **Sentry/GlitchTip instead of OTel.** Not an alternative — complementary. OTel is
  the collection layer; Sentry/GlitchTip is an error-aggregation consumer. Both can
  coexist.
- **Print-style logging (f-strings).** Rejected: unstructured logs are unsearchable
  at scale. Structured JSON logging enables log aggregation and alerting.
