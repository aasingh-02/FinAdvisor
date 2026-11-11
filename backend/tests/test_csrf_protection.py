"""
tests/test_csrf_protection.py
──────────────────────────────
Automated test suite for SEC-VULN-006: Defense-in-Depth CSRF Protection (Hardened).

Verifies:
1. Trusted Origin (settings.frontend_url) accepted on state-changing methods (POST, PUT, PATCH, DELETE).
2. Untrusted Origin rejected with HTTP 403 Forbidden.
3. Safe behavior for missing Origin:
   - Valid Referer matching frontend origin is accepted.
   - Untrusted Referer is rejected with HTTP 403.
4. Safe behavior for missing both Origin and Referer:
   - Permitted for unauthenticated requests or explicit non-browser clients (no session cookie).
   - STRICTLY REJECTED with HTTP 403 Forbidden if cookie-based browser authentication is present.
5. Safe methods (GET, HEAD, OPTIONS) are unaffected by Origin headers or cookies.
6. CORS preflight (OPTIONS) requests continue functioning.
7. Login, registration, and logout flows function properly with trusted Origin.
8. Attack scenarios:
   - Cross-site attempt to trigger logout with untrusted Origin is blocked (403), session preserved.
   - Cross-site attempt with untrusted Referer is blocked (403), session preserved.
   - Attack attempt with cookie but stripped Origin and Referer is blocked (403), session preserved.
9. Explicit non-browser API client authentication:
   - Token passed via 'Authorization: Bearer <token>' succeeds without Origin/Referer and without cookies.
   - Logout via Bearer token invalidates the database session.
10. Security headers (nosniff, DENY) are attached to CSRF 403 responses.
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.database import get_db
from app.main import create_app
from app.middleware.csrf_middleware import get_trusted_origins, normalize_origin
from app.routers.auth import COOKIE_NAME
from app.services import auth_service
from app.utils.rate_limit import limiter


@pytest.fixture(autouse=True)
def reset_limiter_fixture():
    limiter.reset()
    yield
    limiter.reset()


# ── 1. Unit Tests for CSRF Utilities ──────────────────────────────────────────


class TestCSRFUnitUtilities:
    def test_normalize_origin_handles_ports_paths_and_trailing_slashes(self):
        assert normalize_origin("http://localhost:5173") == "http://localhost:5173"
        assert normalize_origin("http://localhost:5173/") == "http://localhost:5173"
        assert normalize_origin("http://localhost:5173/some/path?query=1") == "http://localhost:5173"
        assert normalize_origin("HTTPS://App.FinAdvisor.COM:443/") == "https://app.finadvisor.com:443"

    def test_normalize_origin_empty(self):
        assert normalize_origin("") == ""
        assert normalize_origin(None) == ""

    def test_get_trusted_origins_handles_comma_separated(self, monkeypatch):
        settings = get_settings()
        monkeypatch.setattr(settings, "frontend_url", "http://localhost:5173, https://app.finadvisor.com/")
        origins = get_trusted_origins()
        assert "http://localhost:5173" in origins
        assert "https://app.finadvisor.com" in origins


# ── 2. Middleware Request Validation Tests ────────────────────────────────────


class TestCSRFProtectionMiddleware:
    @pytest.mark.asyncio
    async def test_trusted_origin_accepted_on_post(self):
        """State-changing POST with trusted Origin must be allowed through."""
        settings = get_settings()
        trusted = settings.frontend_url  # "http://localhost:5173"

        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            with patch(
                "app.routers.auth.auth_service.login_user",
                side_effect=ValueError("Invalid credentials"),
            ):
                res = await client.post(
                    "/api/v1/auth/login",
                    json={"email": "u@example.com", "password": "Password123!"},
                    headers={"Origin": trusted},
                )
                # 401 proves request was processed by auth router, NOT blocked by CSRF (403)
                assert res.status_code == 401

    @pytest.mark.asyncio
    async def test_untrusted_origin_rejected_with_403_on_post(self):
        """State-changing POST with untrusted Origin must return HTTP 403."""
        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            res = await client.post(
                "/api/v1/auth/login",
                json={"email": "u@example.com", "password": "Password123!"},
                headers={"Origin": "https://evil-attacker-site.com"},
            )
            assert res.status_code == 403
            assert res.json() == {"detail": "CSRF verification failed: Untrusted Origin."}
            # Security headers must be present on 403 response
            assert res.headers.get("X-Content-Type-Options") == "nosniff"
            assert res.headers.get("X-Frame-Options") == "DENY"

    @pytest.mark.asyncio
    async def test_missing_origin_trusted_referer_accepted(self):
        """If Origin is absent, a Referer matching the frontend origin must be accepted."""
        settings = get_settings()
        trusted_referer = f"{settings.frontend_url}/dashboard/settings"

        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            with patch(
                "app.routers.auth.auth_service.login_user",
                side_effect=ValueError("Invalid credentials"),
            ):
                res = await client.post(
                    "/api/v1/auth/login",
                    json={"email": "u@example.com", "password": "Password123!"},
                    headers={"Referer": trusted_referer},
                )
                assert res.status_code == 401  # Passed CSRF check

    @pytest.mark.asyncio
    async def test_missing_origin_untrusted_referer_rejected(self):
        """If Origin is absent, an untrusted Referer must return HTTP 403."""
        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            res = await client.post(
                "/api/v1/auth/login",
                json={"email": "u@example.com", "password": "Password123!"},
                headers={"Referer": "https://phishing-site.com/login-phish.html"},
            )
            assert res.status_code == 403
            assert res.json() == {"detail": "CSRF verification failed: Untrusted Referer."}

    @pytest.mark.asyncio
    async def test_missing_both_origin_and_referer_allowed_for_unauthenticated_requests(self):
        """Unauthenticated callers (no cookie) without Origin/Referer are permitted to reach auth logic."""
        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            with patch(
                "app.routers.auth.auth_service.login_user",
                side_effect=ValueError("Invalid credentials"),
            ):
                res = await client.post(
                    "/api/v1/auth/login",
                    json={"email": "u@example.com", "password": "Password123!"},
                )
                assert res.status_code == 401  # Passed CSRF check, reached auth service

    @pytest.mark.asyncio
    async def test_missing_both_origin_and_referer_with_cookie_rejected_with_403(self):
        """State-changing request carrying session cookie with missing Origin AND Referer MUST return 403."""
        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            client.cookies.set(COOKIE_NAME, "mock_session_token_12345")
            res = await client.post("/api/v1/auth/logout")

            assert res.status_code == 403
            assert res.json() == {
                "detail": "CSRF verification failed: Missing Origin and Referer on cookie-authenticated request."
            }
            # Security headers must be attached
            assert res.headers.get("X-Content-Type-Options") == "nosniff"
            assert res.headers.get("X-Frame-Options") == "DENY"

    @pytest.mark.asyncio
    async def test_missing_both_origin_and_referer_on_chat_with_cookie_rejected_with_403(self):
        """Advisor chat with session cookie but missing Origin AND Referer must be blocked with 403."""
        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            client.cookies.set(COOKIE_NAME, "mock_session_token_12345")
            res = await client.post(
                "/api/v1/advisor/chat",
                json={"message": "Can I afford a new loan?"},
            )
            assert res.status_code == 403
            assert res.json() == {
                "detail": "CSRF verification failed: Missing Origin and Referer on cookie-authenticated request."
            }

    @pytest.mark.asyncio
    async def test_safe_methods_unaffected_by_untrusted_origin_or_cookies(self):
        """Safe methods (GET, HEAD, OPTIONS) must not be blocked by CSRF checks, even with cookies."""
        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            client.cookies.set(COOKIE_NAME, "any_cookie_token")

            # GET /health with untrusted origin and cookie
            res_get = await client.get("/health", headers={"Origin": "https://evil.com"})
            assert res_get.status_code == 200

            # GET /health without any Origin or Referer
            res_get_no_headers = await client.get("/health")
            assert res_get_no_headers.status_code == 200

            # OPTIONS CORS preflight with trusted origin
            settings = get_settings()
            res_options = await client.options(
                "/api/v1/auth/login",
                headers={
                    "Origin": settings.frontend_url,
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "Content-Type",
                },
            )
            assert res_options.status_code == 200
            assert res_options.headers.get("Access-Control-Allow-Origin") == settings.frontend_url


# ── 3. Integration Tests: Attack Simulation & User Flows ──────────────────────


class TestCSRFAuthenticationIntegration:
    @pytest.mark.asyncio
    async def test_login_and_logout_with_trusted_origin(self, db):
        """Legitimate browser session flow with trusted Origin works from start to finish."""
        app = create_app()

        async def override_db():
            yield db

        app.dependency_overrides[get_db] = override_db

        settings = get_settings()
        trusted = settings.frontend_url

        user = await auth_service.register_user(
            db=db,
            email="csrf_valid@example.com",
            full_name="CSRF Valid User",
            plain_password="Password123!",
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            # 1. Login with trusted Origin
            login_res = await client.post(
                "/api/v1/auth/login",
                json={"email": "csrf_valid@example.com", "password": "Password123!"},
                headers={"Origin": trusted},
            )
            assert login_res.status_code == 200
            token = client.cookies.get(COOKIE_NAME)
            assert token is not None

            # 2. Logout with trusted Origin
            logout_res = await client.post(
                "/api/v1/auth/logout",
                headers={"Origin": trusted},
            )
            assert logout_res.status_code == 200
            assert logout_res.json() == {"message": "Logged out successfully."}

    @pytest.mark.asyncio
    async def test_cross_site_attack_blocked_and_session_preserved(self, db):
        """
        Attacker site tries to force logout of victim by issuing cross-site POST with victim cookie.
        Request must be rejected with 403, and victim session must remain completely intact.
        """
        app = create_app()

        async def override_db():
            yield db

        app.dependency_overrides[get_db] = override_db

        settings = get_settings()
        trusted = settings.frontend_url

        user = await auth_service.register_user(
            db=db,
            email="csrf_victim@example.com",
            full_name="CSRF Victim User",
            plain_password="Password123!",
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            # 1. Legitimate user logs in
            login_res = await client.post(
                "/api/v1/auth/login",
                json={"email": "csrf_victim@example.com", "password": "Password123!"},
                headers={"Origin": trusted},
            )
            assert login_res.status_code == 200
            session_cookie = client.cookies.get(COOKIE_NAME)
            assert session_cookie is not None

            # 2. Attacker site initiates cross-origin request carrying the victim's session cookie
            attack_res = await client.post(
                "/api/v1/auth/logout",
                headers={"Origin": "https://malicious-exploit-hub.com"},
            )
            # Must be stopped cold with 403 Forbidden
            assert attack_res.status_code == 403
            assert attack_res.json() == {"detail": "CSRF verification failed: Untrusted Origin."}

            # 3. Verify victim's session was NOT destroyed by the attack
            active_user = await auth_service.get_user_from_token(db=db, token=session_cookie)
            assert active_user is not None
            assert active_user.id == user.id

            # 4. Victim continues browsing with their valid session
            me_res = await client.get("/api/v1/auth/me", headers={"Origin": trusted})
            assert me_res.status_code == 200
            assert me_res.json()["email"] == "csrf_victim@example.com"

    @pytest.mark.asyncio
    async def test_cross_site_attack_untrusted_referer_blocked_and_session_preserved(self, db):
        """
        Attacker site triggers cross-site POST with an untrusted Referer header.
        Request must be rejected with 403, and victim session must remain completely intact.
        """
        app = create_app()

        async def override_db():
            yield db

        app.dependency_overrides[get_db] = override_db

        settings = get_settings()
        trusted = settings.frontend_url

        user = await auth_service.register_user(
            db=db,
            email="csrf_victim_ref@example.com",
            full_name="CSRF Ref Victim",
            plain_password="Password123!",
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            # 1. Legitimate user logs in
            login_res = await client.post(
                "/api/v1/auth/login",
                json={"email": "csrf_victim_ref@example.com", "password": "Password123!"},
                headers={"Origin": trusted},
            )
            assert login_res.status_code == 200
            session_cookie = client.cookies.get(COOKIE_NAME)
            assert session_cookie is not None

            # 2. Cross-origin request with untrusted Referer (Origin header stripped)
            attack_res = await client.post(
                "/api/v1/auth/logout",
                headers={"Referer": "https://malicious-forum.com/thread/123"},
            )
            assert attack_res.status_code == 403
            assert attack_res.json() == {"detail": "CSRF verification failed: Untrusted Referer."}

            # 3. Victim session remains intact
            active_user = await auth_service.get_user_from_token(db=db, token=session_cookie)
            assert active_user is not None
            assert active_user.id == user.id

    @pytest.mark.asyncio
    async def test_attack_with_cookie_and_missing_origin_referer_blocked_and_session_preserved(self, db):
        """
        An exploit attempts to suppress both Origin and Referer while sending the victim's session cookie.
        Must be rejected with HTTP 403 and the session must remain intact.
        """
        app = create_app()

        async def override_db():
            yield db

        app.dependency_overrides[get_db] = override_db

        settings = get_settings()
        trusted = settings.frontend_url

        user = await auth_service.register_user(
            db=db,
            email="csrf_victim_noheaders@example.com",
            full_name="CSRF NoHeaders Victim",
            plain_password="Password123!",
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            # 1. Legitimate user logs in
            login_res = await client.post(
                "/api/v1/auth/login",
                json={"email": "csrf_victim_noheaders@example.com", "password": "Password123!"},
                headers={"Origin": trusted},
            )
            assert login_res.status_code == 200
            session_cookie = client.cookies.get(COOKIE_NAME)
            assert session_cookie is not None

            # 2. Malicious request with cookie but NO Origin and NO Referer
            attack_res = await client.post("/api/v1/auth/logout")
            assert attack_res.status_code == 403
            assert attack_res.json() == {
                "detail": "CSRF verification failed: Missing Origin and Referer on cookie-authenticated request."
            }

            # 3. Victim's session in the database is untouched
            active_user = await auth_service.get_user_from_token(db=db, token=session_cookie)
            assert active_user is not None
            assert active_user.id == user.id

            # 4. User can still successfully log out when using legitimate frontend Origin
            legit_logout = await client.post(
                "/api/v1/auth/logout",
                headers={"Origin": trusted},
            )
            assert legit_logout.status_code == 200
            assert legit_logout.json() == {"message": "Logged out successfully."}


# ── 4. Non-Browser API Client Authentication (Explicit Bearer Token) ──────────


class TestNonBrowserAPIClientAuthentication:
    @pytest.mark.asyncio
    async def test_non_browser_explicit_token_authentication_flow(self, db):
        """
        Non-browser API clients (mobile apps, CLI tools) authenticate via explicit
        'Authorization: Bearer <token>' header. They transmit neither cookies nor
        Origin/Referer headers, and are fully supported.
        """
        app = create_app()

        async def override_db():
            yield db

        app.dependency_overrides[get_db] = override_db

        # 1. Register user and generate a session token in DB via login_user
        await auth_service.register_user(
            db=db,
            email="api_client@example.com",
            full_name="API Client User",
            plain_password="Password123!",
        )
        user, raw_token = await auth_service.login_user(
            db=db,
            email="api_client@example.com",
            plain_password="Password123!",
        )

        transport = ASGITransport(app=app)
        # Client has NO cookies, NO Origin, and NO Referer headers
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers={"Authorization": f"Bearer {raw_token}"},
        ) as client:
            # 2. Non-browser client calls GET /auth/me
            me_res = await client.get("/api/v1/auth/me")
            assert me_res.status_code == 200
            assert me_res.json()["email"] == "api_client@example.com"

            # 3. Non-browser client calls POST /auth/logout (state-changing)
            # Passes CSRF because no cookie is attached; auth_middleware extracts Bearer token
            logout_res = await client.post("/api/v1/auth/logout")
            assert logout_res.status_code == 200
            assert logout_res.json() == {"message": "Logged out successfully."}

            # 4. Confirm session was revoked in database
            active_user = await auth_service.get_user_from_token(db=db, token=raw_token)
            assert active_user is None

            # 5. Subsequent call with invalidated token returns 401
            subsequent_res = await client.get("/api/v1/auth/me")
            assert subsequent_res.status_code == 401
