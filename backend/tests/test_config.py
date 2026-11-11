"""
tests/test_config.py
────────────────────
Automated test suite for SEC-VULN-009: Unused Mandatory session_secret_key.

Verifies:
1. Settings loads cleanly when SESSION_SECRET_KEY is absent from environment.
2. Backward compatibility: Settings loads cleanly when legacy SESSION_SECRET_KEY is present (ignored via extra='ignore').
3. session_secret_key attribute is no longer required on Settings.
4. FastAPI application starts and serves requests without SESSION_SECRET_KEY configured.
5. Authentication, session creation, login, and logout remain fully operational.
"""

import os
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings, get_settings
from app.database import get_db
from app.main import create_app
from app.routers.auth import COOKIE_NAME
from app.services import auth_service


class TestConfigurationSettings:
    """Verify application configuration behavior without the unused session_secret_key."""

    def test_settings_loads_without_session_secret_key(self, monkeypatch):
        """Settings must instantiate cleanly when SESSION_SECRET_KEY is completely unset."""
        monkeypatch.delenv("SESSION_SECRET_KEY", raising=False)
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/testdb")

        # Instantiate Settings with an empty env_file to ensure no fallback reads
        settings = Settings(
            database_url="postgresql+asyncpg://user:pass@localhost:5432/testdb",
            _env_file=None,
        )
        assert settings.database_url == "postgresql+asyncpg://user:pass@localhost:5432/testdb"
        assert settings.session_expire_hours == 24
        assert not hasattr(settings, "session_secret_key")

    def test_settings_ignores_legacy_session_secret_key(self, monkeypatch):
        """Settings must gracefully ignore legacy SESSION_SECRET_KEY if still present in .env."""
        monkeypatch.setenv("SESSION_SECRET_KEY", "legacy_unused_secret_32_bytes_value")
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/testdb")

        settings = Settings(
            database_url="postgresql+asyncpg://user:pass@localhost:5432/testdb",
            _env_file=None,
        )
        assert settings.database_url == "postgresql+asyncpg://user:pass@localhost:5432/testdb"
        assert not hasattr(settings, "session_secret_key")

    def test_session_secret_key_not_in_settings_fields(self):
        """session_secret_key must not be in Settings model_fields."""
        assert "session_secret_key" not in Settings.model_fields


class TestAppStartupAndAuthWithoutSecretKey:
    """Verify application startup, login, logout, and session lifecycle work without session_secret_key."""

    @pytest.mark.asyncio
    async def test_app_starts_and_health_check_succeeds(self):
        """FastAPI application initializes and responds to /health."""
        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            res = await client.get("/health")
            assert res.status_code == 200
            assert res.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_full_auth_lifecycle_without_session_secret_key(self, db):
        """
        Verify complete user registration, login, session creation, authenticated request,
        and logout operate seamlessly without any session_secret_key.
        """
        app = create_app()

        async def override_db():
            yield db

        app.dependency_overrides[get_db] = override_db

        settings = get_settings()
        trusted = settings.frontend_url

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            # 1. Register new user
            reg_res = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": "nosecret@example.com",
                    "full_name": "No Secret User",
                    "password": "ValidPass123!",
                },
                headers={"Origin": trusted},
            )
            assert reg_res.status_code == 201
            session_cookie = client.cookies.get(COOKIE_NAME)
            assert session_cookie is not None

            # 2. Authenticated request using cookie
            me_res = await client.get("/api/v1/auth/me", headers={"Origin": trusted})
            assert me_res.status_code == 200
            assert me_res.json()["email"] == "nosecret@example.com"

            # 3. Logout
            logout_res = await client.post("/api/v1/auth/logout", headers={"Origin": trusted})
            assert logout_res.status_code == 200
            assert logout_res.json()["message"] == "Logged out successfully."

            # 4. Confirm session was revoked
            unauth_res = await client.get("/api/v1/auth/me", headers={"Origin": trusted})
            assert unauth_res.status_code == 401
