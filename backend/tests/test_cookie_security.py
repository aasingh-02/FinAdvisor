"""
tests/test_cookie_security.py
───────────────────────────────
Automated tests for SEC-VULN-003: Session Cookie Security & Deletion Attributes.

Verifies:
1. _set_session_cookie and _clear_session_cookie use identical security attributes.
2. In development (HTTP): secure=False so localhost cookies function without HTTPS.
3. In production (HTTPS): secure=True so cookies carry the Secure attribute on creation and deletion.
4. Logout endpoint removes the database session (using token_hash).
5. The client is strictly prohibited from continuing to use the revoked session token.
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from starlette.responses import Response

from app.config import Settings, get_settings
from app.database import get_db
from app.main import create_app
from app.models.session import Session
from app.models.user import User
from app.routers.auth import (
    COOKIE_NAME,
    _clear_session_cookie,
    _session_cookie_attributes,
    _set_session_cookie,
)
from app.services import auth_service
from app.utils.rate_limit import limiter
from app.utils.security import hash_session_token


# ── 1. Unit Tests for Cookie Helper Functions ──────────────────────────────────


class TestCookieSecurityHelpers:
    def test_set_and_clear_cookie_dev_attributes(self, monkeypatch):
        """In development, Secure flag must be False (HTTP localhost compatible)."""
        settings = get_settings()
        monkeypatch.setattr(settings, "environment", "development")

        res_set = Response()
        _set_session_cookie(res_set, "sample_dev_token_123")
        set_cookie_header = res_set.headers.get("set-cookie", "")

        assert f"{COOKIE_NAME}=sample_dev_token_123" in set_cookie_header
        assert "HttpOnly" in set_cookie_header
        assert "Path=/" in set_cookie_header
        assert "SameSite=lax" in set_cookie_header
        assert "Secure" not in set_cookie_header

        res_clear = Response()
        _clear_session_cookie(res_clear)
        clear_cookie_header = res_clear.headers.get("set-cookie", "")

        assert f'{COOKIE_NAME}=""' in clear_cookie_header
        assert "Max-Age=0" in clear_cookie_header
        assert "HttpOnly" in clear_cookie_header
        assert "Path=/" in clear_cookie_header
        assert "SameSite=lax" in clear_cookie_header
        assert "Secure" not in clear_cookie_header

    def test_set_and_clear_cookie_prod_attributes(self, monkeypatch):
        """In production, Secure flag must be True on both creation and deletion."""
        settings = get_settings()
        monkeypatch.setattr(settings, "environment", "production")

        res_set = Response()
        _set_session_cookie(res_set, "sample_prod_token_456")
        set_cookie_header = res_set.headers.get("set-cookie", "")

        assert f"{COOKIE_NAME}=sample_prod_token_456" in set_cookie_header
        assert "HttpOnly" in set_cookie_header
        assert "Path=/" in set_cookie_header
        assert "SameSite=lax" in set_cookie_header
        assert "Secure" in set_cookie_header

        res_clear = Response()
        _clear_session_cookie(res_clear)
        clear_cookie_header = res_clear.headers.get("set-cookie", "")

        assert f'{COOKIE_NAME}=""' in clear_cookie_header
        assert "Max-Age=0" in clear_cookie_header
        assert "HttpOnly" in clear_cookie_header
        assert "Path=/" in clear_cookie_header
        assert "SameSite=lax" in clear_cookie_header
        assert "Secure" in clear_cookie_header


# ── 2. Integration Tests with Full App & Database ──────────────────────────────


class TestLogoutFlowAndInvalidation:
    @pytest.mark.asyncio
    async def test_logout_in_development_clears_cookie_and_deletes_db_session(self, db, monkeypatch):
        """
        In development:
        - Logout returns Set-Cookie with Max-Age=0 and secure=False.
        - Database session row is deleted.
        - Subsequent request with the same token is rejected with 401.
        """
        settings = get_settings()
        monkeypatch.setattr(settings, "environment", "development")
        limiter.reset()

        app = create_app()

        async def override_db():
            yield db

        app.dependency_overrides[get_db] = override_db

        # 1. Register test user
        user = await auth_service.register_user(
            db=db,
            email="cookie_dev@example.com",
            full_name="Cookie Dev User",
            plain_password="SecurePassword123!",
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers={"Origin": "http://localhost:5173"},
        ) as client:
            # 2. Login
            login_res = await client.post(
                "/api/v1/auth/login",
                json={"email": "cookie_dev@example.com", "password": "SecurePassword123!"},
            )
            assert login_res.status_code == 200
            token = client.cookies.get(COOKIE_NAME)
            assert token is not None

            # Verify session exists in DB via token_hash
            user_from_token = await auth_service.get_user_from_token(db=db, token=token)
            assert user_from_token is not None
            assert user_from_token.id == user.id

            # 3. Call /auth/logout
            logout_res = await client.post("/api/v1/auth/logout")
            assert logout_res.status_code == 200
            assert logout_res.json() == {"message": "Logged out successfully."}

            clear_header = logout_res.headers.get("set-cookie", "")
            assert f'{COOKIE_NAME}=""' in clear_header
            assert "Max-Age=0" in clear_header
            assert "HttpOnly" in clear_header
            assert "Secure" not in clear_header

            # 4. Verify session is deleted from database
            user_after_logout = await auth_service.get_user_from_token(db=db, token=token)
            assert user_after_logout is None

            # 5. Verify client using the revoked token cannot access protected /auth/me
            client.cookies.set(COOKIE_NAME, token)
            me_res = await client.get("/api/v1/auth/me")
            assert me_res.status_code == 401
            assert "Not authenticated" in me_res.json()["detail"]

    @pytest.mark.asyncio
    async def test_logout_in_production_includes_secure_flag(self, db, monkeypatch):
        """
        In production:
        - Logout returns Set-Cookie with Max-Age=0 AND Secure attribute.
        - Database session row is deleted.
        - Subsequent request is rejected with 401.
        """
        settings = get_settings()
        monkeypatch.setattr(settings, "environment", "production")
        limiter.reset()

        app = create_app()

        async def override_db():
            yield db

        app.dependency_overrides[get_db] = override_db

        user = await auth_service.register_user(
            db=db,
            email="cookie_prod@example.com",
            full_name="Cookie Prod User",
            plain_password="SecurePassword123!",
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="https://testserver",
            headers={"Origin": "http://localhost:5173"},
        ) as client:
            login_res = await client.post(
                "/api/v1/auth/login",
                json={"email": "cookie_prod@example.com", "password": "SecurePassword123!"},
            )
            assert login_res.status_code == 200
            login_cookie_header = login_res.headers.get("set-cookie", "")
            assert "Secure" in login_cookie_header

            token = client.cookies.get(COOKIE_NAME)
            assert token is not None

            # Call /auth/logout
            logout_res = await client.post("/api/v1/auth/logout")
            assert logout_res.status_code == 200

            clear_header = logout_res.headers.get("set-cookie", "")
            assert f'{COOKIE_NAME}=""' in clear_header
            assert "Max-Age=0" in clear_header
            assert "HttpOnly" in clear_header
            assert "SameSite=lax" in clear_header
            assert "Secure" in clear_header

            # Confirm token no longer resolves in DB
            assert await auth_service.get_user_from_token(db=db, token=token) is None

            # Confirm rejected on /auth/me
            client.cookies.set(COOKIE_NAME, token)
            me_res = await client.get("/api/v1/auth/me")
            assert me_res.status_code == 401

    @pytest.mark.asyncio
    async def test_staging_https_login_and_logout_with_cookie_secure_env(self, db, monkeypatch):
        """
        In HTTPS staging (ENVIRONMENT=staging + COOKIE_SECURE=true):
        - Environment is NOT disguised as production (is_production is False).
        - Login and logout both emit identical Secure, HttpOnly, SameSite=lax, Path=/ flags.
        """
        monkeypatch.setenv("ENVIRONMENT", "staging")
        monkeypatch.setenv("COOKIE_SECURE", "true")
        monkeypatch.setenv("ALLOW_IN_MEMORY_RATE_LIMIT", "true")
        get_settings.cache_clear()
        try:
            current_settings = get_settings()
            assert current_settings.is_production is False
            assert current_settings.cookie_secure is True
            limiter.reset()

            app = create_app()

            async def override_db():
                yield db

            app.dependency_overrides[get_db] = override_db

            await auth_service.register_user(
                db=db,
                email="cookie_staging@example.com",
                full_name="Cookie Staging User",
                plain_password="SecurePassword123!",
            )

            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="https://testserver",
                headers={"Origin": "http://localhost:5173"},
            ) as client:
                login_res = await client.post(
                    "/api/v1/auth/login",
                    json={"email": "cookie_staging@example.com", "password": "SecurePassword123!"},
                )
                assert login_res.status_code == 200
                login_header = login_res.headers.get("set-cookie", "")
                assert "HttpOnly" in login_header
                assert "Path=/" in login_header
                assert "SameSite=lax" in login_header
                assert "Secure" in login_header

                logout_res = await client.post("/api/v1/auth/logout")
                assert logout_res.status_code == 200
                clear_header = logout_res.headers.get("set-cookie", "")
                assert f'{COOKIE_NAME}=""' in clear_header
                assert "Max-Age=0" in clear_header
                assert "HttpOnly" in clear_header
                assert "Path=/" in clear_header
                assert "SameSite=lax" in clear_header
                assert "Secure" in clear_header
        finally:
            get_settings.cache_clear()


# ── 3. Configurable COOKIE_SECURE Tests (FIN-SEC-03) ───────────────────────────


_TEST_DB_URL = "postgresql+asyncpg://user:pass@localhost:5432/testdb"


class TestConfigurableCookieSecure:
    """Verify FIN-SEC-03 COOKIE_SECURE configuration matrix and safety invariants."""

    def test_development_without_override_defaults_to_false(self, monkeypatch):
        """Development without COOKIE_SECURE defaults to Secure=False."""
        monkeypatch.delenv("COOKIE_SECURE", raising=False)
        monkeypatch.delenv("ENVIRONMENT", raising=False)

        cfg = Settings(database_url=_TEST_DB_URL, environment="development", _env_file=None)
        assert cfg.is_production is False
        assert cfg.cookie_secure_override is None
        assert cfg.cookie_secure is False

    def test_production_without_override_defaults_to_true(self, monkeypatch):
        """Production without COOKIE_SECURE defaults to Secure=True."""
        monkeypatch.delenv("COOKIE_SECURE", raising=False)

        cfg = Settings(database_url=_TEST_DB_URL, environment="production", _env_file=None)
        assert cfg.is_production is True
        assert cfg.cookie_secure_override is None
        assert cfg.cookie_secure is True

    def test_staging_with_cookie_secure_true_env(self, monkeypatch):
        """Staging HTTPS environments can enable COOKIE_SECURE=true without faking production."""
        monkeypatch.setenv("ENVIRONMENT", "staging")
        monkeypatch.setenv("COOKIE_SECURE", "true")

        cfg = Settings(database_url=_TEST_DB_URL, _env_file=None)
        assert cfg.environment == "staging"
        assert cfg.is_production is False
        assert cfg.cookie_secure_override is True
        assert cfg.cookie_secure is True

    def test_staging_with_cookie_secure_false_env(self, monkeypatch):
        """Staging HTTP environments can explicitly set COOKIE_SECURE=false."""
        monkeypatch.setenv("ENVIRONMENT", "staging")
        monkeypatch.setenv("COOKIE_SECURE", "false")

        cfg = Settings(database_url=_TEST_DB_URL, _env_file=None)
        assert cfg.environment == "staging"
        assert cfg.is_production is False
        assert cfg.cookie_secure_override is False
        assert cfg.cookie_secure is False

    def test_production_rejects_cookie_secure_false_via_env_and_init(self, monkeypatch):
        """Production must reject explicit COOKIE_SECURE=false configuration."""
        with pytest.raises(ValidationError, match="COOKIE_SECURE cannot be set to false in production"):
            Settings(
                database_url=_TEST_DB_URL,
                environment="production",
                cookie_secure=False,
                _env_file=None,
            )

        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("COOKIE_SECURE", "false")
        with pytest.raises(ValidationError, match="COOKIE_SECURE cannot be set to false in production"):
            Settings(database_url=_TEST_DB_URL, _env_file=None)

    def test_production_always_enforces_secure_even_if_override_mutated(self, monkeypatch):
        """Runtime defense-in-depth: production always evaluates cookie_secure=True."""
        settings = get_settings()
        monkeypatch.setattr(settings, "environment", "production")
        monkeypatch.setattr(settings, "cookie_secure_override", False)

        assert settings.is_production is True
        assert settings.cookie_secure is True

    def test_blank_cookie_secure_env_behaves_as_unset(self, monkeypatch):
        """Empty COOKIE_SECURE= string in .env/environment falls back to environment defaults."""
        monkeypatch.setenv("COOKIE_SECURE", "   ")

        dev_cfg = Settings(database_url=_TEST_DB_URL, environment="development", _env_file=None)
        assert dev_cfg.cookie_secure_override is None
        assert dev_cfg.cookie_secure is False

        prod_cfg = Settings(database_url=_TEST_DB_URL, environment="production", _env_file=None)
        assert prod_cfg.cookie_secure_override is None
        assert prod_cfg.cookie_secure is True

    def test_invalid_cookie_secure_value_raises_validation_error(self, monkeypatch):
        """Non-boolean COOKIE_SECURE values fail loudly instead of silently weakening security."""
        monkeypatch.setenv("COOKIE_SECURE", "not_a_boolean")
        with pytest.raises(ValidationError):
            Settings(database_url=_TEST_DB_URL, environment="staging", _env_file=None)

    @pytest.mark.parametrize(
        ("env_name", "override_val", "expected_secure"),
        [
            ("development", None, False),
            ("development", True, True),
            ("staging", True, True),
            ("staging", False, False),
            ("production", None, True),
            ("production", True, True),
        ],
    )
    def test_cookie_creation_and_deletion_attributes_match(
        self, monkeypatch, env_name, override_val, expected_secure
    ):
        """_set_session_cookie and _clear_session_cookie always share identical security flags."""
        settings = get_settings()
        monkeypatch.setattr(settings, "environment", env_name)
        monkeypatch.setattr(settings, "cookie_secure_override", override_val)

        attrs = _session_cookie_attributes()
        assert attrs == {
            "httponly": True,
            "secure": expected_secure,
            "samesite": "lax",
            "path": "/",
        }

        res_set = Response()
        _set_session_cookie(res_set, "test_session_token_xyz")
        set_header = res_set.headers.get("set-cookie", "")

        res_clear = Response()
        _clear_session_cookie(res_clear)
        clear_header = res_clear.headers.get("set-cookie", "")

        for header in (set_header, clear_header):
            assert "HttpOnly" in header
            assert "SameSite=lax" in header
            assert "Path=/" in header
            if expected_secure:
                assert "Secure" in header
            else:
                assert "Secure" not in header

        assert "Max-Age=0" in clear_header
        assert f'{COOKIE_NAME}=""' in clear_header

    def test_samesite_none_for_cross_origin_deployments(self, monkeypatch):
        """COOKIE_SAMESITE=none enables cross-origin session cookies when HTTPS is active."""
        settings = get_settings()
        monkeypatch.setattr(settings, "environment", "production")
        monkeypatch.setattr(settings, "cookie_samesite", "none")

        attrs = _session_cookie_attributes()
        assert attrs["samesite"] == "none"
        assert attrs["secure"] is True

        res = Response()
        _set_session_cookie(res, "cross_origin_token")
        header = res.headers.get("set-cookie", "")
        assert "SameSite=none" in header
        assert "Secure" in header
        assert "HttpOnly" in header

    def test_samesite_none_rejected_without_secure(self):
        """SameSite=none strictly requires Secure=True; rejected otherwise."""
        with pytest.raises(ValueError, match="COOKIE_SAMESITE cannot be 'none' when cookie_secure is False"):
            Settings(
                database_url="sqlite+aiosqlite:///:memory:",
                environment="development",
                cookie_secure=False,
                cookie_samesite="none",
            )
