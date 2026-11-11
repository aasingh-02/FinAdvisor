"""
tests/test_security_headers.py
───────────────────────────────
Automated tests for SEC-VULN-004: HTTP Security Headers.

Verifies:
1. X-Content-Type-Options: nosniff on all responses (200, 401, 404, 429, 500).
2. X-Frame-Options: DENY on all responses.
3. Referrer-Policy: strict-origin-when-cross-origin on all responses.
4. Content-Security-Policy (CSP) applied appropriately without breaking /docs or API clients.
5. Strict-Transport-Security (HSTS) max-age=31536000; includeSubDomains enforced ONLY in production.
6. Rate limit (429) responses carry security headers alongside rate limit headers.
7. CORS preflight (OPTIONS) requests preserve CORS headers and security headers.
"""

from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.main import create_app
from app.middleware.security_headers import CSP_POLICY, PROD_API_CSP_POLICY
from app.utils.rate_limit import limiter


@pytest.fixture(autouse=True)
def reset_limiter_fixture():
    limiter.reset()
    yield
    limiter.reset()


class TestSecurityHeadersDevelopment:
    @pytest.mark.asyncio
    async def test_200_response_contains_security_headers_in_dev(self, monkeypatch):
        """Standard 200 responses must have nosniff, DENY, Referrer-Policy, and CSP; no HSTS in dev."""
        settings = get_settings()
        monkeypatch.setattr(settings, "environment", "development")

        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            res = await client.get("/health")
            assert res.status_code == 200

            assert res.headers.get("X-Content-Type-Options") == "nosniff"
            assert res.headers.get("X-Frame-Options") == "DENY"
            assert res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
            assert res.headers.get("Content-Security-Policy") == CSP_POLICY
            # HSTS must NOT be set in development (HTTP localhost)
            assert "Strict-Transport-Security" not in res.headers

    @pytest.mark.asyncio
    async def test_404_response_contains_security_headers(self, monkeypatch):
        """Not Found (404) responses must include security headers."""
        settings = get_settings()
        monkeypatch.setattr(settings, "environment", "development")

        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            res = await client.get("/api/v1/non-existent-endpoint")
            assert res.status_code == 404
            assert res.headers.get("X-Content-Type-Options") == "nosniff"
            assert res.headers.get("X-Frame-Options") == "DENY"
            assert res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
            assert res.headers.get("Content-Security-Policy") == CSP_POLICY

    @pytest.mark.asyncio
    async def test_401_response_contains_security_headers(self, monkeypatch):
        """Unauthorized (401) responses must include security headers."""
        settings = get_settings()
        monkeypatch.setattr(settings, "environment", "development")

        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            res = await client.get("/api/v1/auth/me")
            assert res.status_code == 401
            assert res.headers.get("X-Content-Type-Options") == "nosniff"
            assert res.headers.get("X-Frame-Options") == "DENY"
            assert res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
            assert res.headers.get("Content-Security-Policy") == CSP_POLICY

    @pytest.mark.asyncio
    async def test_429_rate_limit_response_contains_security_headers(self, monkeypatch):
        """Rate limit (429) responses must contain both Retry-After and all security headers."""
        settings = get_settings()
        monkeypatch.setattr(settings, "environment", "development")

        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            with patch(
                "app.routers.auth.auth_service.login_user",
                side_effect=ValueError("Invalid credentials"),
            ):
                for _ in range(5):
                    await client.post(
                        "/api/v1/auth/login",
                        json={"email": "u@example.com", "password": "Password123!"},
                    )

                res429 = await client.post(
                    "/api/v1/auth/login",
                    json={"email": "u@example.com", "password": "Password123!"},
                )
                assert res429.status_code == 429
                assert "Retry-After" in res429.headers
                assert res429.headers.get("X-Content-Type-Options") == "nosniff"
                assert res429.headers.get("X-Frame-Options") == "DENY"
                assert res429.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
                assert res429.headers.get("Content-Security-Policy") == CSP_POLICY

    @pytest.mark.asyncio
    async def test_500_error_response_contains_security_headers(self, monkeypatch):
        """Unhandled server error (500) responses from global exception handler must include security headers."""
        settings = get_settings()
        monkeypatch.setattr(settings, "environment", "development")

        app = create_app()

        @app.get("/test-internal-error")
        async def trigger_error():
            raise RuntimeError("Database connection suddenly dropped")

        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            res = await client.get("/test-internal-error")
            assert res.status_code == 500
            assert res.headers.get("X-Content-Type-Options") == "nosniff"
            assert res.headers.get("X-Frame-Options") == "DENY"
            assert res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
            assert res.headers.get("Content-Security-Policy") == CSP_POLICY

    @pytest.mark.asyncio
    async def test_swagger_and_openapi_docs_work_with_csp(self, monkeypatch):
        """API documentation endpoints (/docs, /redoc, /openapi.json) must load with CSP header."""
        settings = get_settings()
        monkeypatch.setattr(settings, "environment", "development")

        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            docs_res = await client.get("/docs")
            assert docs_res.status_code == 200
            assert docs_res.headers.get("Content-Security-Policy") == CSP_POLICY
            assert "swagger" in docs_res.text.lower()

            openapi_res = await client.get("/openapi.json")
            assert openapi_res.status_code == 200
            assert openapi_res.headers.get("Content-Security-Policy") == CSP_POLICY

            redoc_res = await client.get("/redoc")
            assert redoc_res.status_code == 200
            assert redoc_res.headers.get("Content-Security-Policy") == CSP_POLICY

    @pytest.mark.asyncio
    async def test_cors_preflight_preserves_cors_and_security_headers(self, monkeypatch):
        """OPTIONS preflight must preserve Access-Control headers alongside security headers."""
        settings = get_settings()
        monkeypatch.setattr(settings, "environment", "development")

        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            res = await client.options(
                "/api/v1/auth/login",
                headers={
                    "Origin": settings.frontend_url,
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "Content-Type",
                },
            )
            assert res.status_code == 200
            assert res.headers.get("Access-Control-Allow-Origin") == settings.frontend_url
            assert res.headers.get("Access-Control-Allow-Credentials") == "true"
            assert res.headers.get("X-Content-Type-Options") == "nosniff"
            assert res.headers.get("X-Frame-Options") == "DENY"


class TestSecurityHeadersProduction:
    @pytest.mark.asyncio
    async def test_production_enforces_hsts_on_responses(self, monkeypatch):
        """In production, Strict-Transport-Security must be present with max-age=31536000; includeSubDomains."""
        settings = get_settings()
        monkeypatch.setattr(settings, "environment", "production")

        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="https://testserver") as client:
            # 200 OK
            res200 = await client.get("/health")
            assert res200.status_code == 200
            assert res200.headers.get("Strict-Transport-Security") == "max-age=31536000; includeSubDomains"
            assert res200.headers.get("X-Content-Type-Options") == "nosniff"
            assert res200.headers.get("X-Frame-Options") == "DENY"

            # 401 Unauthorized
            res401 = await client.get("/api/v1/auth/me")
            assert res401.status_code == 401
            assert res401.headers.get("Strict-Transport-Security") == "max-age=31536000; includeSubDomains"

            # 404 Not Found
            res404 = await client.get("/api/v1/unknown-endpoint")
            assert res404.status_code == 404
            assert res404.headers.get("Strict-Transport-Security") == "max-age=31536000; includeSubDomains"

    @pytest.mark.asyncio
    async def test_production_enforces_strict_api_csp_without_unsafe_inline_or_cdn(self, monkeypatch):
        """In production (/docs disabled), backend CSP must be maximally strict without unsafe-inline or CDN."""
        settings = get_settings()
        monkeypatch.setattr(settings, "environment", "production")

        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="https://api.finadvisor.example") as client:
            res = await client.get("/health")
            assert res.status_code == 200
            csp = res.headers.get("Content-Security-Policy")
            assert csp == PROD_API_CSP_POLICY
            assert "'unsafe-inline'" not in csp
            assert "cdn.jsdelivr.net" not in csp
            assert "object-src 'none'" in csp
            assert "frame-ancestors 'none'" in csp
            assert "connect-src 'self'" in csp
            assert "*" not in csp

    @pytest.mark.asyncio
    async def test_production_cross_origin_and_same_origin_cors_with_security_headers(self, monkeypatch):
        """Backend allows configured frontend origin in both cross-origin and same-origin deployments."""
        settings = get_settings()
        monkeypatch.setattr(settings, "environment", "production")

        # 1. Cross-origin deployment (e.g. app.finadvisor.example -> api.finadvisor.example)
        monkeypatch.setattr(settings, "frontend_url", "https://app.finadvisor.example")
        app_cross = create_app()
        async with AsyncClient(
            transport=ASGITransport(app=app_cross),
            base_url="https://api.finadvisor.example",
        ) as client:
            res = await client.options(
                "/api/v1/auth/login",
                headers={
                    "Origin": "https://app.finadvisor.example",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "Content-Type",
                },
            )
            assert res.status_code == 200
            assert res.headers.get("Access-Control-Allow-Origin") == "https://app.finadvisor.example"
            assert res.headers.get("Access-Control-Allow-Credentials") == "true"
            assert res.headers.get("Content-Security-Policy") == PROD_API_CSP_POLICY
            assert res.headers.get("Strict-Transport-Security") == "max-age=31536000; includeSubDomains"

        # 2. Same-origin reverse-proxy deployment (e.g. https://finadvisor.example)
        monkeypatch.setattr(settings, "frontend_url", "https://finadvisor.example")
        app_same = create_app()
        async with AsyncClient(
            transport=ASGITransport(app=app_same),
            base_url="https://finadvisor.example",
        ) as client:
            res = await client.get(
                "/health",
                headers={"Origin": "https://finadvisor.example"},
            )
            assert res.status_code == 200
            assert res.headers.get("Access-Control-Allow-Origin") == "https://finadvisor.example"
            assert res.headers.get("Content-Security-Policy") == PROD_API_CSP_POLICY
