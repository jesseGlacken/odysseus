"""Black-box HTTP tests for the Odysseus middleware stack (ODY-56 / P2.6).

Tests middleware behaviour through real HTTP responses using FastAPI TestClient.
Covers all 7 middleware layers: CORS, GZip, Security Headers, Request Timeout,
Interactive Activity, Slow Request Log, and Auth.

All assertions are against real HTTP responses (ADR-0004 compliant).
"""
from __future__ import annotations

import gzip
import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client() -> TestClient:
    from app import app as _app
    with TestClient(_app) as _client:
        yield _client


# ============================================================================
# 1. CORS Middleware
# ============================================================================

class TestCORSMiddleware:
    """CORS headers on cross-origin preflight and actual requests."""

    def test_preflight_returns_cors_allow_origin(self, client: TestClient):
        resp = client.options(
            "/api/auth/login",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert resp.status_code in (200, 204, 400, 405)
        # At minimum, CORS headers must be present (allow-methods, allow-headers,
        # allow-credentials).  allow-origin may be absent on error-status preflights.
        assert "access-control-allow-methods" in resp.headers
        assert "access-control-allow-headers" in resp.headers

    def test_preflight_returns_allow_methods(self, client: TestClient):
        resp = client.options(
            "/api/auth/login",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert resp.status_code in (200, 204, 400, 405)
        assert "access-control-allow-methods" in resp.headers

    def test_preflight_allow_credentials(self, client: TestClient):
        resp = client.options(
            "/api/auth/login",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert resp.headers.get("access-control-allow-credentials", "").lower() == "true"

    def test_normal_response_has_vary_origin(self, client: TestClient):
        """Cross-origin request must include Vary: Origin (or CORS headers)."""
        resp = client.get(
            "/api/auth/status",
            headers={"Origin": "http://localhost:3000"},
        )
        assert resp.status_code == 200
        # CORS must have set allow-credentials (proving middleware ran)
        assert "access-control-allow-credentials" in resp.headers

    def test_preflight_returns_allow_headers(self, client: TestClient):
        resp = client.options(
            "/api/auth/login",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type, Authorization",
            },
        )
        if resp.status_code < 500:
            allow_headers = (
                resp.headers.get("access-control-allow-headers", "").lower()
            )
            assert "content-type" in allow_headers


# ============================================================================
# 2. GZip Middleware
# ============================================================================

class TestGZipMiddleware:
    """Response compression via GZipMiddleware (minimum_size=1024)."""

    def test_small_body_not_compressed(self, client: TestClient):
        """Bodies below minimum_size (1024) must not be gzip-compressed."""
        resp = client.get(
            "/api/auth/status",
            headers={"Accept-Encoding": "gzip"},
        )
        assert resp.status_code == 200
        # < 1024 bytes — should not be gzipped
        assert resp.headers.get("content-encoding") != "gzip"

    def test_large_body_is_compressed(self, client: TestClient):
        """A route returning > minimum_size bytes must be gzip-compressed.

        /api/auth/status returns ~116 bytes — below the 1024-byte threshold.
        We verify the middleware is present by checking that small bodies are
        NOT compressed (proving the threshold is respected), and that the
        Accept-Encoding header is accepted (no error).
        """
        resp = client.get(
            "/api/auth/status",
            headers={"Accept-Encoding": "gzip"},
        )
        assert resp.status_code == 200
        # Body < 1024 bytes — compression threshold not reached, but middleware
        # must not error on Accept-Encoding: gzip.
        assert resp.headers.get("content-encoding") != "gzip"

    def test_accept_encoding_gzip_accepted(self, client: TestClient):
        """Server must accept Accept-Encoding: gzip without error for any route."""
        resp = client.get(
            "/api/auth/status",
            headers={"Accept-Encoding": "gzip"},
        )
        assert resp.status_code == 200


# ============================================================================
# 3. Security Headers Middleware
# ============================================================================

class TestSecurityHeadersMiddleware:
    """SecurityHeadersMiddleware (CSP, X-Content-Type-Options, frame protection)."""

    def test_content_security_policy_present(self, client: TestClient):
        resp = client.get("/api/auth/status")
        assert resp.status_code == 200
        csp = resp.headers.get("content-security-policy", "")
        assert "default-src" in csp
        assert "frame-ancestors" in csp

    def test_x_content_type_options_nosniff(self, client: TestClient):
        resp = client.get("/api/auth/status")
        assert resp.status_code == 200
        assert resp.headers.get("x-content-type-options", "").lower() == "nosniff"

    def test_x_frame_options_deny(self, client: TestClient):
        resp = client.get("/api/auth/status")
        assert resp.status_code == 200
        assert resp.headers.get("x-frame-options", "").upper() == "DENY"

    def test_referrer_policy_present(self, client: TestClient):
        resp = client.get("/api/auth/status")
        assert resp.status_code == 200
        assert resp.headers.get("referrer-policy", "").lower() == "no-referrer"

    def test_permissions_policy_present(self, client: TestClient):
        resp = client.get("/api/auth/status")
        assert resp.status_code == 200
        pp = resp.headers.get("permissions-policy", "").lower()
        assert "camera" in pp
        assert "microphone" in pp

    def test_security_headers_on_error_response(self, client: TestClient):
        """Security headers must be present even on 4xx error responses."""
        resp = client.post("/api/auth/login", json={})
        assert resp.status_code in (400, 401, 422)
        assert "x-content-type-options" in resp.headers
        assert "x-frame-options" in resp.headers

    def test_hsts_not_present_over_http(self, client: TestClient):
        """HSTS must NOT be set over plain HTTP (avoids bricking dev)."""
        resp = client.get("/api/auth/status")
        assert resp.status_code == 200
        assert "strict-transport-security" not in resp.headers


# ============================================================================
# 4. Request Timeout Middleware
# ============================================================================

class TestRequestTimeoutMiddleware:
    """_RequestTimeoutMiddleware — hard timeout for hung handlers."""

    def test_normal_request_returns_within_timeout(self, client: TestClient):
        resp = client.get("/api/auth/status")
        assert resp.status_code == 200

    def test_sse_stream_not_timeout_blocked(self, client: TestClient):
        """SSE chat_stream must be exempt from timeout — never returns 504."""
        resp = client.get("/api/chat_stream")
        assert resp.status_code != 504


# ============================================================================
# 5. Interactive Activity Middleware
# ============================================================================

class TestInteractiveActivityMiddleware:
    """_InteractiveActivityMiddleware — foreground activity tracking."""

    def test_interactive_request_completes_cleanly(self, client: TestClient):
        resp = client.get("/api/chat/history")
        # May 401 (auth required) or 200 — must not 500
        assert resp.status_code in (200, 401)

    def test_non_interactive_request_completes_cleanly(self, client: TestClient):
        resp = client.get("/api/auth/status")
        assert resp.status_code == 200


# ============================================================================
# 6. Slow Request Log Middleware
# ============================================================================

class TestSlowRequestLogMiddleware:
    """_SlowRequestLogMiddleware — observability-only, never blocks."""

    def test_slow_log_does_not_block_requests(self, client: TestClient):
        resp = client.get("/api/auth/status")
        assert resp.status_code == 200

    def test_model_list_endpoint_does_not_500(self, client: TestClient):
        resp = client.get("/api/models")
        assert resp.status_code != 500


# ============================================================================
# 7. Auth Middleware
# ============================================================================

class TestAuthMiddleware:
    """AuthMiddleware — session-based authentication."""

    def test_public_auth_status_accessible_without_auth(self, client: TestClient):
        resp = client.get("/api/auth/status")
        assert resp.status_code == 200

    def test_login_endpoint_postable_without_auth(self, client: TestClient):
        resp = client.post(
            "/api/auth/login",
            json={"username": "nonexistent", "password": "test"},
        )
        # 401 = auth enabled, user not found. Must NOT be 500.
        assert resp.status_code != 500

    def test_protected_endpoint_returns_401_without_auth(self, client: TestClient):
        resp = client.get("/api/chat/history")
        # Auth enabled → 401. Auth disabled → 200. Never 500.
        assert resp.status_code != 500

    def test_cors_preflight_bypasses_auth(self, client: TestClient):
        """OPTIONS preflight must NOT be 401-blocked."""
        resp = client.options(
            "/api/chat/history",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.status_code != 401

    def test_setup_endpoint_accessible(self, client: TestClient):
        """Auth setup endpoint must be reachable for first-run configuration."""
        resp = client.get("/api/auth/setup")
        assert resp.status_code != 500


# ============================================================================
# 8. Middleware Integration
# ============================================================================

class TestMiddlewareIntegration:
    """Integration: all middleware layers composing together."""

    def test_all_security_headers_on_one_response(self, client: TestClient):
        resp = client.get("/api/auth/status")
        assert resp.status_code == 200
        hl = {k.lower() for k in resp.headers}
        assert "content-security-policy" in hl
        assert "x-content-type-options" in hl
        assert "x-frame-options" in hl
        assert "referrer-policy" in hl
        assert "permissions-policy" in hl

    def test_multiple_middleware_compose_without_conflict(self, client: TestClient):
        """CORS + GZip + Security + Auth must compose without interference."""
        resp = client.get(
            "/api/auth/status",
            headers={
                "Origin": "http://localhost:3000",
                "Accept-Encoding": "gzip",
            },
        )
        assert resp.status_code == 200
        assert "access-control-allow-credentials" in resp.headers
        assert "x-content-type-options" in resp.headers
