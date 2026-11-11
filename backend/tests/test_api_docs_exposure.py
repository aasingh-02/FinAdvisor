"""
tests/test_api_docs_exposure.py
─────────────────────────────────
Automated tests for SEC-VULN-005: Interactive OpenAPI / Swagger Documentation Exposed in Production.

Verifies:
1. In development (environment="development"):
   - /docs returns 200 with Swagger UI.
   - /redoc returns 200 with ReDoc UI.
   - /openapi.json returns 200 with valid OpenAPI schema.
   - /api/docs redirects to /docs.
2. In production (environment="production"):
   - /docs returns HTTP 404 Not Found.
   - /redoc returns HTTP 404 Not Found.
   - /openapi.json returns HTTP 404 Not Found.
   - /api/docs returns HTTP 404 Not Found (no route registered).
   - Standard API endpoints (such as /health) remain fully operational (200 OK).
   - Security headers (nosniff, DENY, HSTS) are maintained on all responses.
   - No accidental exposure of documentation through alternative paths.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.main import create_app


class TestApiDocsDevelopment:
    @pytest.mark.asyncio
    async def test_swagger_ui_accessible_in_dev(self, monkeypatch):
        """In development, /docs must be accessible and render Swagger UI."""
        settings = get_settings()
        monkeypatch.setattr(settings, "environment", "development")

        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            res = await client.get("/docs")
            assert res.status_code == 200
            assert "swagger-ui" in res.text.lower() or "swagger" in res.text.lower()

    @pytest.mark.asyncio
    async def test_redoc_accessible_in_dev(self, monkeypatch):
        """In development, /redoc must be accessible and render ReDoc."""
        settings = get_settings()
        monkeypatch.setattr(settings, "environment", "development")

        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            res = await client.get("/redoc")
            assert res.status_code == 200
            assert "redoc" in res.text.lower()

    @pytest.mark.asyncio
    async def test_openapi_json_accessible_in_dev(self, monkeypatch):
        """In development, /openapi.json must return the complete OpenAPI specification."""
        settings = get_settings()
        monkeypatch.setattr(settings, "environment", "development")

        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            res = await client.get("/openapi.json")
            assert res.status_code == 200
            data = res.json()
            assert "openapi" in data
            assert "paths" in data
            assert "/api/v1/auth/login" in data["paths"]

    @pytest.mark.asyncio
    async def test_api_docs_redirect_in_dev(self, monkeypatch):
        """In development, /api/docs redirects to /docs."""
        settings = get_settings()
        monkeypatch.setattr(settings, "environment", "development")

        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver", follow_redirects=False) as client:
            res = await client.get("/api/docs")
            assert res.status_code in (301, 302, 307, 308)
            assert res.headers.get("location") == "/docs"


class TestApiDocsProduction:
    @pytest.mark.asyncio
    async def test_docs_returns_404_in_production(self, monkeypatch):
        """In production, /docs must return 404 Not Found."""
        settings = get_settings()
        monkeypatch.setattr(settings, "environment", "production")

        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="https://testserver") as client:
            res = await client.get("/docs")
            assert res.status_code == 404
            assert res.headers.get("X-Content-Type-Options") == "nosniff"
            assert res.headers.get("Strict-Transport-Security") == "max-age=31536000; includeSubDomains"

    @pytest.mark.asyncio
    async def test_redoc_returns_404_in_production(self, monkeypatch):
        """In production, /redoc must return 404 Not Found."""
        settings = get_settings()
        monkeypatch.setattr(settings, "environment", "production")

        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="https://testserver") as client:
            res = await client.get("/redoc")
            assert res.status_code == 404
            assert res.headers.get("X-Content-Type-Options") == "nosniff"

    @pytest.mark.asyncio
    async def test_openapi_json_returns_404_in_production(self, monkeypatch):
        """In production, /openapi.json must return 404 Not Found."""
        settings = get_settings()
        monkeypatch.setattr(settings, "environment", "production")

        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="https://testserver") as client:
            res = await client.get("/openapi.json")
            assert res.status_code == 404
            assert res.headers.get("X-Content-Type-Options") == "nosniff"

    @pytest.mark.asyncio
    async def test_api_docs_redirect_returns_404_in_production(self, monkeypatch):
        """In production, /api/docs must not exist and return 404 Not Found."""
        settings = get_settings()
        monkeypatch.setattr(settings, "environment", "production")

        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="https://testserver", follow_redirects=False) as client:
            res = await client.get("/api/docs")
            assert res.status_code == 404

    @pytest.mark.asyncio
    async def test_production_api_endpoints_work_normally(self, monkeypatch):
        """Normal API endpoints (/health) continue to work in production with security headers."""
        settings = get_settings()
        monkeypatch.setattr(settings, "environment", "production")

        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="https://testserver") as client:
            res = await client.get("/health")
            assert res.status_code == 200
            assert res.json() == {"status": "ok", "environment": "production"}
            assert res.headers.get("Strict-Transport-Security") == "max-age=31536000; includeSubDomains"
            assert res.headers.get("X-Content-Type-Options") == "nosniff"
            assert res.headers.get("X-Frame-Options") == "DENY"

    @pytest.mark.asyncio
    async def test_no_accidental_docs_exposure_on_alternate_paths(self, monkeypatch):
        """Common alternative paths for documentation must all return 404 in production."""
        settings = get_settings()
        monkeypatch.setattr(settings, "environment", "production")

        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="https://testserver") as client:
            for path in ["/docs/", "/swagger", "/swagger.json", "/api/openapi.json", "/v1/docs"]:
                res = await client.get(path)
                assert res.status_code == 404, f"Path {path} unexpectedly returned {res.status_code}"
