# Odysseus Middleware Stack

The Odysseus backend applies **7 middleware layers** to every HTTP request
(and the `AuthMiddleware` conditionally when `AUTH_ENABLED` is true).  They
are executed in the order Starlette processes them — outermost first.

## Layer Order (outermost → innermost)

| # | Middleware | File | Purpose |
|---|-----------|------|---------|
| 1 | `AuthMiddleware` | `app.py:356` | Session-based auth for protected routes |
| 2 | `CORSMiddleware` | `app.py:130` | Cross-Origin Resource Sharing headers |
| 3 | `GZipMiddleware` | `app.py:156` | Response body compression (≥1024 bytes) |
| 4 | `SecurityHeadersMiddleware` | `core/middleware.py:59` | CSP, XSS, frame, HSTS, referrer, permissions |
| 5 | `_RequestTimeoutMiddleware` | `app.py:187` | Hard timeout (30s) for hung handlers |
| 6 | `_InteractiveActivityMiddleware` | `app.py:201` | Foreground activity tracking |
| 7 | `_SlowRequestLogMiddleware` | `app.py:218` | Logs requests slower than 0.75s |

## 1. AuthMiddleware

**File:** `app.py:356`

Session-cookie auth. Checks every request (except exempt paths and CORS
preflights) for a valid session.  Unauthenticated requests to protected routes
receive **401 Unauthorized**.

**Exempt paths:**
`/api/auth/setup`, `/api/auth/signup`, `/api/auth/login`,
`/api/auth/logout`, `/api/auth/status`, `/api/auth/features`,
`/api/auth/settings`, `/api/auth/verify-totp`

CORS preflights (`OPTIONS` + `Access-Control-Request-Method`) always pass
through so `CORSMiddleware` can answer them.

## 2. CORSMiddleware

**File:** `app.py:130` (Starlette `CORSMiddleware`)

**Allowed origins:** configured via `ALLOWED_ORIGINS` env var
(default: `http://localhost,http://127.0.0.1`).

**Allowed methods:** `GET, POST, PUT, PATCH, DELETE`

**Allowed headers:** `Accept, Authorization, Content-Type, X-API-Key,
X-Auth-Token, X-Odysseus-Internal-Token, X-Odysseus-Owner, X-Requested-With,
X-TZ-Offset`

**Credentials:** `access-control-allow-credentials: true` (required for
session-cookie auth).

## 3. GZipMiddleware

**File:** `app.py:156` (Starlette `GZipMiddleware`)

Compresses response bodies ≥1024 bytes with gzip (level 6).  Excludes
`text/event-stream` responses (SSE chat/research streams are never buffered).

## 4. SecurityHeadersMiddleware

**File:** `core/middleware.py:59`

Adds the following headers to every response:

| Header | Value |
|--------|-------|
| `X-Content-Type-Options` | `nosniff` |
| `Referrer-Policy` | `no-referrer` |
| `Permissions-Policy` | `camera=(), microphone=(self), geolocation=()` |
| `X-Frame-Options` | `DENY` (or `SAMEORIGIN` for PDF preview) |
| `Content-Security-Policy` | Nonce-based CSP with jsDelivr CDN allowlist |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` (HTTPS only) |

**Per-route CSP variations:**
- **Default** — `'nonce-{random}'` for scripts, `'unsafe-inline'` for styles,
  jsDelivr CDN allowed for scripts/styles/fonts.
- **Tool render** (`/api/tools/*/render`) — no framing headers applied.
- **PDF preview** (`/api/document/*/render-pdf`) — `X-Frame-Options: SAMEORIGIN`,
  `frame-ancestors 'self'`.
- **Visual report** (`/api/research/report/*`) — `'unsafe-inline'` for both
  scripts and styles (self-contained HTML pages).

## 5. _RequestTimeoutMiddleware

**File:** `app.py:187`

Aborts requests that take longer than `REQUEST_HARD_TIMEOUT` seconds (default
30s) with a **504 Gateway Timeout**.

**Exempt prefixes:** `/api/chat_stream`, `/api/chat/resume`,
`/api/shell_stream`, `/api/research/stream`, `/api/model/probe_stream`,
`/api/stream`.

## 6. _InteractiveActivityMiddleware

**File:** `app.py:201`

Tracks foreground user activity.  For interactive endpoints (chat sends,
tool calls, etc.), it stops background tasks that would compete for model
resources, then acquires an activity gate that ensures foreground requests
are prioritized.

## 7. _SlowRequestLogMiddleware

**File:** `app.py:218`

Observability-only.  Logs requests that take ≥0.75s at WARNING level:
`slow_request method=<METHOD> path=<PATH> status=<STATUS> elapsed=<SECONDS>s`

Threshold configurable via `ODYSSEUS_SLOW_REQUEST_LOG_SECONDS` env var.
Never blocks or rejects requests.

## Testing

Middleware tests live in `apps/api/tests/test_middleware_stack.py` (ODY-56).
All tests are **black-box HTTP tests** using FastAPI `TestClient` — no mocks,
no internal imports of middleware classes.

Run: `cd apps/api && PYTHONPATH=src:src/src uv run pytest tests/test_middleware_stack.py -v`
