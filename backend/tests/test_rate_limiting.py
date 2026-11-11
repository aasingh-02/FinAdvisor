"""
tests/test_rate_limiting.py
───────────────────────────
Automated test suite for SEC-VULN-001 (API Rate Limiting).

Tests:
1. Client IP resolution & spoofing protection (trusted proxy vs untrusted peer).
2. Key generation hierarchy (authenticated state -> cookie -> IP fallback).
3. POST /api/v1/auth/login: 5 requests/min per IP limit + 429 + Retry-After.
4. POST /api/v1/auth/register: 5 requests/min per IP limit + 429 + Retry-After.
5. POST /api/v1/advisor/chat: 30 requests/min per authenticated user limit.
6. Multi-tenant isolation: User A hitting limit does not block User B on the same IP.
7. Health check (/health) exemption: 40 requests without 429.
8. Limiter reset functionality.
"""

import math
import time
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from starlette.requests import Request

from app.config import Settings, get_settings
from app.database import get_db
from app.main import create_app
from app.models.user import User
from app.utils.rate_limit import (
    get_client_ip,
    get_user_or_ip_key,
    limiter,
)
from app.utils.security import hash_session_token

_TEST_DB_URL = "postgresql+asyncpg://user:pass@localhost:5432/testdb"


@pytest.fixture(autouse=True)
def reset_limiter_and_settings():
    """Reset rate limiter state and restore default proxy settings before each test."""
    limiter.reset()
    settings = get_settings()
    original_trusted = settings.trusted_proxy_ips
    original_enabled = settings.rate_limit_enabled
    yield
    limiter.reset()
    settings.trusted_proxy_ips = original_trusted
    settings.rate_limit_enabled = original_enabled


# ── 1. Client IP & Key Generation Unit Tests ──────────────────────────────────


class TestRateLimitUtility:
    def test_get_client_ip_direct(self):
        """When no proxies are configured, returns peer client IP."""
        settings = get_settings()
        settings.trusted_proxy_ips = ""

        req = Request({
            "type": "http",
            "client": ("192.168.1.100", 45000),
            "headers": [],
        })
        assert get_client_ip(req) == "192.168.1.100"

    def test_get_client_ip_untrusted_proxy_ignores_spoofed_header(self):
        """Spoofed X-Forwarded-For is ignored if peer is not in trusted_proxy_ips."""
        settings = get_settings()
        settings.trusted_proxy_ips = "10.0.0.1"

        req = Request({
            "type": "http",
            "client": ("192.168.1.100", 45000),
            "headers": [(b"x-forwarded-for", b"203.0.113.195")],
        })
        assert get_client_ip(req) == "192.168.1.100"

    def test_get_client_ip_trusted_proxy_extracts_client(self):
        """When peer is a trusted proxy, extracts originating client IP from X-Forwarded-For."""
        settings = get_settings()
        settings.trusted_proxy_ips = "10.0.0.1, 10.0.0.2"

        req = Request({
            "type": "http",
            "client": ("10.0.0.1", 45000),
            "headers": [(b"x-forwarded-for", b"203.0.113.50, 10.0.0.1")],
        })
        assert get_client_ip(req) == "203.0.113.50"

    def test_get_user_or_ip_key_authenticated_state(self):
        """When request.state.user is set, uses user:<id> as rate limit key."""
        uid = uuid.uuid4()
        user = User(
            id=uid,
            email="test@example.com",
            full_name="Test User",
            hashed_password="hash",
            is_active=True,
        )

        req = Request({
            "type": "http",
            "client": ("192.168.1.50", 45000),
            "headers": [],
        })
        req.state.user = user
        assert get_user_or_ip_key(req) == f"user:{uid}"

    def test_get_user_or_ip_key_cookie_fallback(self):
        """When request.state has no user, falls back to hashed session cookie token."""
        req = Request({
            "type": "http",
            "client": ("192.168.1.50", 45000),
            "headers": [(b"cookie", b"session_token=test_token_abc123")],
        })
        expected_key = f"token:{hash_session_token('test_token_abc123')[:16]}"
        assert get_user_or_ip_key(req) == expected_key

    def test_get_user_or_ip_key_ip_fallback(self):
        """When no user state or cookie is present, falls back to client IP."""
        req = Request({
            "type": "http",
            "client": ("192.168.1.50", 45000),
            "headers": [],
        })
        assert get_user_or_ip_key(req) == "ip:192.168.1.50"


# ── 2. Auth Endpoints Rate Limiting (5/min per IP) ─────────────────────────────


class TestAuthRateLimiting:
    @pytest.mark.asyncio
    async def test_login_rate_limiting_5_per_minute(self):
        """
        POST /api/v1/auth/login allows 5 requests per minute per IP.
        The 6th request must return HTTP 429 with Retry-After header.
        """
        app = create_app()

        async def dummy_db():
            yield AsyncMock()

        app.dependency_overrides[get_db] = dummy_db

        with patch(
            "app.routers.auth.auth_service.login_user",
            side_effect=ValueError("Invalid credentials"),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://testserver",
                headers={"Origin": "http://localhost:5173"},
            ) as client:
                # 5 allowed attempts
                for i in range(5):
                    res = await client.post(
                        "/api/v1/auth/login",
                        json={
                            "email": "user@example.com",
                            "password": "Password123!",
                        },
                    )
                    assert res.status_code == 401, f"Attempt {i+1} got {res.status_code}"

                # 6th attempt must be blocked by rate limiter
                res6 = await client.post(
                    "/api/v1/auth/login",
                    json={
                        "email": "user@example.com",
                        "password": "Password123!",
                    },
                )
                assert res6.status_code == 429
                assert "Retry-After" in res6.headers
                retry_after = int(res6.headers["Retry-After"])
                assert 1 <= retry_after <= 60
                assert res6.headers.get("X-RateLimit-Limit") == "5"
                assert res6.headers.get("X-RateLimit-Remaining") == "0"

                data = res6.json()
                assert "Rate limit exceeded" in data["detail"]

    @pytest.mark.asyncio
    async def test_register_rate_limiting_5_per_minute(self):
        """
        POST /api/v1/auth/register allows 5 requests per minute per IP.
        The 6th request must return HTTP 429 with Retry-After header.
        """
        app = create_app()

        async def dummy_db():
            yield AsyncMock()

        app.dependency_overrides[get_db] = dummy_db

        with patch(
            "app.routers.auth.auth_service.register_user",
            side_effect=ValueError("Email already registered"),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://testserver",
                headers={"Origin": "http://localhost:5173"},
            ) as client:
                for i in range(5):
                    res = await client.post(
                        "/api/v1/auth/register",
                        json={
                            "email": "user@example.com",
                            "full_name": "Test User",
                            "password": "Password123!",
                        },
                    )
                    assert res.status_code == 409, f"Attempt {i+1} got {res.status_code}"

                # 6th attempt must be 429
                res6 = await client.post(
                    "/api/v1/auth/register",
                    json={
                        "email": "user@example.com",
                        "full_name": "Test User",
                        "password": "Password123!",
                    },
                )
                assert res6.status_code == 429
                assert "Retry-After" in res6.headers
                assert res6.headers.get("X-RateLimit-Limit") == "5"

    @pytest.mark.asyncio
    async def test_rate_limit_reset_clears_quota(self):
        """Verifies that calling limiter.reset() clears the rate limit state."""
        app = create_app()

        async def dummy_db():
            yield AsyncMock()

        app.dependency_overrides[get_db] = dummy_db

        with patch(
            "app.routers.auth.auth_service.login_user",
            side_effect=ValueError("Invalid credentials"),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://testserver",
                headers={"Origin": "http://localhost:5173"},
            ) as client:
                for _ in range(5):
                    await client.post(
                        "/api/v1/auth/login",
                        json={
                            "email": "user@example.com",
                            "password": "Password123!",
                        },
                    )

                # 6th is 429
                res_blocked = await client.post(
                    "/api/v1/auth/login",
                    json={
                        "email": "user@example.com",
                        "password": "Password123!",
                    },
                )
                assert res_blocked.status_code == 429

                # Reset storage
                limiter.reset()

                # Next attempt should be allowed through again
                res_after_reset = await client.post(
                    "/api/v1/auth/login",
                    json={
                        "email": "user@example.com",
                        "password": "Password123!",
                    },
                )
                assert res_after_reset.status_code == 401


# ── 3. Advisor Chat Rate Limiting (30/min per user) & Multi-Tenant Isolation ──


class TestAdvisorChatRateLimiting:
    @pytest.mark.asyncio
    async def test_advisor_chat_rate_limiting_30_per_minute(self):
        """
        POST /api/v1/advisor/chat allows 30 requests per minute per authenticated user.
        The 31st request returns HTTP 429 with Retry-After header.
        """
        app = create_app()

        async def dummy_db():
            yield AsyncMock()

        app.dependency_overrides[get_db] = dummy_db

        test_user = User(
            id=uuid.uuid4(),
            email="advisor_user@example.com",
            full_name="Advisor User",
            hashed_password="hash",
            is_active=True,
        )

        fake_reply = {
            "reply": "Deterministic advisory reply",
            "context_used": "GENERAL",
            "financial_snapshot": None,
            "disclaimer": "Informational only.",
            "is_fallback": True,
            "model_used": "deterministic-rules-engine",
        }

        with patch(
            "app.middleware.auth_middleware.get_user_from_token",
            return_value=test_user,
        ), patch(
            "app.routers.advisor.ai_advisor_service.generate_advisor_chat_response",
            AsyncMock(return_value=fake_reply),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://testserver",
                headers={"Origin": "http://localhost:5173"},
            ) as client:
                client.cookies.set("session_token", "valid_session_token")

                # 30 requests succeed
                for i in range(30):
                    res = await client.post(
                        "/api/v1/advisor/chat",
                        json={"message": "Can I afford a new loan?"},
                    )
                    assert res.status_code == 200, f"Call {i+1} got {res.status_code}"

                # 31st request triggers rate limit
                res31 = await client.post(
                    "/api/v1/advisor/chat",
                    json={"message": "Can I afford a new loan?"},
                )
                assert res31.status_code == 429
                assert "Retry-After" in res31.headers
                assert res31.headers.get("X-RateLimit-Limit") == "30"
                assert res31.headers.get("X-RateLimit-Remaining") == "0"

    @pytest.mark.asyncio
    async def test_advisor_chat_multi_tenant_user_isolation(self):
        """
        Two users sharing the same IP address have independent quotas.
        User A exceeding 30 requests/min does NOT block User B.
        """
        app = create_app()

        async def dummy_db():
            yield AsyncMock()

        app.dependency_overrides[get_db] = dummy_db

        user_a = User(
            id=uuid.uuid4(),
            email="user_a@example.com",
            full_name="User A",
            hashed_password="hash",
            is_active=True,
        )
        user_b = User(
            id=uuid.uuid4(),
            email="user_b@example.com",
            full_name="User B",
            hashed_password="hash",
            is_active=True,
        )

        def mock_get_user(db, token):
            if token == "token_user_a":
                return user_a
            elif token == "token_user_b":
                return user_b
            return None

        fake_reply = {
            "reply": "Deterministic reply",
            "context_used": "GENERAL",
            "financial_snapshot": None,
            "disclaimer": "Informational only.",
            "is_fallback": True,
            "model_used": "deterministic-rules-engine",
        }

        with patch(
            "app.middleware.auth_middleware.get_user_from_token",
            side_effect=mock_get_user,
        ), patch(
            "app.routers.advisor.ai_advisor_service.generate_advisor_chat_response",
            AsyncMock(return_value=fake_reply),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://testserver",
                headers={"Origin": "http://localhost:5173"},
            ) as client:
                # User A consumes all 30 requests from the client IP
                client.cookies.set("session_token", "token_user_a")
                for _ in range(30):
                    res = await client.post(
                        "/api/v1/advisor/chat",
                        json={"message": "Query from User A"},
                    )
                    assert res.status_code == 200

                # User A's 31st request is blocked
                res_a_blocked = await client.post(
                    "/api/v1/advisor/chat",
                    json={"message": "Query from User A"},
                )
                assert res_a_blocked.status_code == 429

                # User B on the EXACT same client IP is NOT blocked
                client.cookies.set("session_token", "token_user_b")
                res_b = await client.post(
                    "/api/v1/advisor/chat",
                    json={"message": "Query from User B"},
                )
                assert res_b.status_code == 200


# ── 4. Health Check Exemption & Rate Limiting Bypass ──────────────────────────


class TestExemptionsAndConfiguration:
    @pytest.mark.asyncio
    async def test_health_check_exempt_from_rate_limiting(self):
        """
        GET /health is exempt from rate limiting.
        40 consecutive calls must all return HTTP 200.
        """
        app = create_app()
        transport = ASGITransport(app=app)

        async with AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            for i in range(40):
                res = await client.get("/health")
                assert res.status_code == 200, f"Health check #{i+1} failed"
                assert res.json() == {
                    "status": "ok",
                    "environment": get_settings().environment,
                }


# ── 5. Trusted Proxy CIDR Resolution & Header Hardening (FIN-SEC-04) ──────────


def _make_proxy_request(
    peer_ip: str,
    forwarded_headers: list[tuple[bytes, bytes]] | None = None,
) -> Request:
    """Build a minimal Starlette HTTP Request with explicit peer IP and headers."""
    return Request({
        "type": "http",
        "client": (peer_ip, 45000),
        "headers": forwarded_headers or [],
    })


class TestTrustedProxyConfiguration:
    def test_empty_trusted_proxy_ips_uses_direct_client_ip(self):
        """Empty or whitespace TRUSTED_PROXY_IPS never trusts X-Forwarded-For."""
        settings = get_settings()
        for raw_cfg in ("", "   ", " , , "):
            settings.trusted_proxy_ips = raw_cfg
            req = _make_proxy_request(
                "198.51.100.12",
                [(b"x-forwarded-for", b"203.0.113.99")],
            )
            assert get_client_ip(req) == "198.51.100.12"

    def test_ipv4_and_ipv6_cidr_matching(self):
        """Supports single IPs and IPv4/IPv6 CIDR ranges when validating the TCP peer."""
        settings = get_settings()
        settings.trusted_proxy_ips = "10.0.0.0/16, 172.16.0.0/12, 2001:db8:1::/48, ::1"

        # IPv4 CIDR match (peer inside 10.0.0.0/16)
        req_v4_cidr = _make_proxy_request(
            "10.0.42.19",
            [(b"x-forwarded-for", b"198.51.100.25")],
        )
        assert get_client_ip(req_v4_cidr) == "198.51.100.25"

        # IPv4 dual-stack mapped peer (::ffff:172.20.1.5 inside 172.16.0.0/12)
        req_mapped = _make_proxy_request(
            "::ffff:172.20.1.5",
            [(b"x-forwarded-for", b"198.51.100.30")],
        )
        assert get_client_ip(req_mapped) == "198.51.100.30"

        # IPv6 CIDR match + canonicalizes client IPv6 formatting
        req_v6_cidr = _make_proxy_request(
            "2001:db8:1::abcd",
            [(b"x-forwarded-for", b"2001:0db8:85a3:0000:0000:8a2e:0370:7334")],
        )
        assert get_client_ip(req_v6_cidr) == "2001:db8:85a3::8a2e:370:7334"

        # Localhost IPv6 trusted proxy match (non-canonical ::1 form)
        req_v6_loopback = _make_proxy_request(
            "0:0:0:0:0:0:0:1",
            [(b"x-forwarded-for", b"203.0.113.77")],
        )
        assert get_client_ip(req_v6_loopback) == "203.0.113.77"

    def test_spoofed_leftmost_xff_behind_trusted_proxy_uses_rightmost_untrusted(self):
        """
        Walks X-Forwarded-For right-to-left stripping trusted hops so client-forged
        left-hand values cannot spoof client identity.
        """
        settings = get_settings()
        settings.trusted_proxy_ips = "10.0.0.0/16, 172.16.0.10"

        # Single trusted proxy appends real client after attacker-forged header
        req_single = _make_proxy_request(
            "10.0.2.5",
            [(b"x-forwarded-for", b"1.2.3.4, 198.51.100.77")],
        )
        assert get_client_ip(req_single) == "198.51.100.77"

        # Multiple trusted proxies across separate X-Forwarded-For headers
        req_multi_header = _make_proxy_request(
            "10.0.2.5",
            [
                (b"x-forwarded-for", b"9.9.9.9, 198.51.100.88"),
                (b"x-forwarded-for", b"172.16.0.10"),
            ],
        )
        assert get_client_ip(req_multi_header) == "198.51.100.88"

    @pytest.mark.parametrize(
        "malformed_xff",
        [
            "",
            "   ",
            " , , ",
            "unknown",
            "999.999.999.999",
            "203.0.113.50:8080",
            "2001:db8::1%eth0",
            "203.0.113.50, not_an_ip",
            "<script>alert(1)</script>",
        ],
    )
    def test_malformed_or_empty_forwarded_headers_fall_back_to_peer_ip(self, malformed_xff):
        """Malformed, empty, or non-IP forwarded values fall back safely to TCP peer IP."""
        settings = get_settings()
        settings.trusted_proxy_ips = "10.0.0.0/24"

        req = _make_proxy_request(
            "10.0.0.5",
            [(b"x-forwarded-for", malformed_xff.encode("utf-8"))],
        )
        assert get_client_ip(req) == "10.0.0.5"

    def test_left_side_garbage_does_not_prevent_reading_right_side_proxy_ip(self):
        """Attacker sending garbage in XFF still gets rate-limited by proxy-appended IP."""
        settings = get_settings()
        settings.trusted_proxy_ips = "10.0.0.0/24"

        req = _make_proxy_request(
            "10.0.0.5",
            [(b"x-forwarded-for", b"evil_spoof, 198.51.100.45")],
        )
        assert get_client_ip(req) == "198.51.100.45"

    def test_untrusted_peer_outside_cidr_cannot_use_forwarded_headers(self):
        """Arbitrary client outside TRUSTED_PROXY_IPS cannot forge client IP."""
        settings = get_settings()
        settings.trusted_proxy_ips = "10.0.0.0/24, 2001:db8:1::/48"

        req = _make_proxy_request(
            "10.0.1.5",  # outside 10.0.0.0/24
            [(b"x-forwarded-for", b"198.51.100.1")],
        )
        assert get_client_ip(req) == "10.0.1.5"

    @pytest.mark.parametrize("wildcard_value", ["0.0.0.0/0", "::/0", "*", "10.0.0.1, 0.0.0.0/0"])
    def test_wildcard_proxy_ranges_blocked_in_settings_and_runtime(self, wildcard_value):
        """Catch-all proxy CIDRs/wildcards are rejected by Settings and ignored at runtime."""
        with pytest.raises(ValidationError, match="forbidden in TRUSTED_PROXY_IPS"):
            Settings(
                database_url=_TEST_DB_URL,
                trusted_proxy_ips=wildcard_value,
                _env_file=None,
            )

        # Even if mutated at runtime on Settings, arbitrary peers are never trusted
        settings = get_settings()
        settings.trusted_proxy_ips = wildcard_value
        req = _make_proxy_request(
            "203.0.113.200",
            [(b"x-forwarded-for", b"198.51.100.9")],
        )
        assert get_client_ip(req) == "203.0.113.200"

    def test_invalid_trusted_proxy_config_rejected_and_runtime_resilient(self):
        """Invalid TRUSTED_PROXY_IPS fails Settings validation and never crashes runtime."""
        with pytest.raises(ValidationError):
            Settings(
                database_url=_TEST_DB_URL,
                trusted_proxy_ips="not-a-cidr",
                _env_file=None,
            )

        settings = get_settings()
        settings.trusted_proxy_ips = "not-a-cidr, 10.0.0.0/24"
        assert get_client_ip(
            _make_proxy_request("10.0.0.8", [(b"x-forwarded-for", b"198.51.100.11")])
        ) == "198.51.100.11"


class TestTrustedProxyAuthRateLimiting:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("endpoint", "service_target", "service_error", "payload", "expected_status"),
        [
            (
                "/api/v1/auth/login",
                "app.routers.auth.auth_service.login_user",
                ValueError("Invalid credentials"),
                {"email": "proxy@example.com", "password": "Password123!"},
                401,
            ),
            (
                "/api/v1/auth/register",
                "app.routers.auth.auth_service.register_user",
                ValueError("Email already registered"),
                {
                    "email": "proxy@example.com",
                    "full_name": "Proxy User",
                    "password": "Password123!",
                },
                409,
            ),
        ],
    )
    async def test_auth_endpoints_isolate_rate_limits_by_resolved_client_ip_behind_trusted_proxy(
        self, endpoint, service_target, service_error, payload, expected_status
    ):
        """
        Behind a trusted proxy CIDR (e.g. AWS ALB/Nginx 10.0.0.0/16), Client A hitting
        the 5/min auth rate limit returns 429 on attempt #6 while Client B behind the
        exact same proxy peer still succeeds.
        """
        settings = get_settings()
        settings.trusted_proxy_ips = "10.0.0.0/16"

        app = create_app()

        async def dummy_db():
            yield AsyncMock()

        app.dependency_overrides[get_db] = dummy_db

        with patch(service_target, side_effect=service_error):
            transport = ASGITransport(app=app, client=("10.0.1.25", 45000))
            async with AsyncClient(
                transport=transport,
                base_url="http://testserver",
                headers={"Origin": "http://localhost:5173"},
            ) as client:
                for _ in range(5):
                    res = await client.post(
                        endpoint,
                        json=payload,
                        headers={"X-Forwarded-For": "198.51.100.10, 10.0.1.25"},
                    )
                    assert res.status_code == expected_status

                res_blocked = await client.post(
                    endpoint,
                    json=payload,
                    headers={"X-Forwarded-For": "198.51.100.10, 10.0.1.25"},
                )
                assert res_blocked.status_code == 429

                # Different client behind the SAME trusted proxy peer has an independent quota
                res_other_client = await client.post(
                    endpoint,
                    json=payload,
                    headers={"X-Forwarded-For": "198.51.100.20, 10.0.1.25"},
                )
                assert res_other_client.status_code == expected_status

    @pytest.mark.asyncio
    async def test_untrusted_client_cannot_bypass_login_rate_limit_by_rotating_xff(self):
        """
        An untrusted peer rotating X-Forwarded-For values still shares a single 5/min
        rate-limit bucket anchored to its true peer IP.
        """
        settings = get_settings()
        settings.trusted_proxy_ips = "10.0.0.0/16"

        app = create_app()

        async def dummy_db():
            yield AsyncMock()

        app.dependency_overrides[get_db] = dummy_db

        with patch(
            "app.routers.auth.auth_service.login_user",
            side_effect=ValueError("Invalid credentials"),
        ):
            transport = ASGITransport(app=app, client=("203.0.113.99", 45000))
            async with AsyncClient(
                transport=transport,
                base_url="http://testserver",
                headers={"Origin": "http://localhost:5173"},
            ) as client:
                for idx in range(5):
                    res = await client.post(
                        "/api/v1/auth/login",
                        json={"email": "attacker@example.com", "password": "Password123!"},
                        headers={"X-Forwarded-For": f"198.51.100.{idx + 1}"},
                    )
                    assert res.status_code == 401

                res_blocked = await client.post(
                    "/api/v1/auth/login",
                    json={"email": "attacker@example.com", "password": "Password123!"},
                    headers={"X-Forwarded-For": "198.51.100.250"},
                )
                assert res_blocked.status_code == 429
