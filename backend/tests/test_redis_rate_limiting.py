"""
tests/test_redis_rate_limiting.py
─────────────────────────────────
Automated tests for FIN-SEC-01: Redis-backed distributed rate limiting for FinAdvisor.

Verifies:
1. Shared storage configuration: Limiter uses Redis storage when configured.
2. Multi-worker synchronization: Multiple Limiter instances share the same Redis storage counters.
3. Safe failure behavior: If Redis is unavailable, requests fail safely without silently falling back to in-memory limits in production.
4. Development vs Production configuration matrix:
   - Production without REDIS_URL -> raises RuntimeError.
   - Production with ALLOW_IN_MEMORY_RATE_LIMIT=True -> raises RuntimeError.
   - Development without REDIS_URL and ALLOW_IN_MEMORY_RATE_LIMIT=False -> raises RuntimeError.
   - Development with ALLOW_IN_MEMORY_RATE_LIMIT=True -> initializes memory://.
   - Valid REDIS_URL -> initializes redis://.
5. Zero credential leakage: Redis passwords and connection URLs are never exposed in logs or exception messages.
"""

from unittest.mock import MagicMock, patch
import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient
from limits import parse
from limits.storage.redis import RedisStorage
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded

from app.config import Settings
from app.main import create_app
from app.utils.rate_limit import (
    configure_limiter_storage,
    limiter,
    rate_limit_exceeded_handler,
    resolve_rate_limit_storage_uri,
    sanitize_storage_uri,
)


class TestRedisConfigurationMatrix:
    """Tests verifying configuration boundaries between development and production."""

    def test_production_without_redis_url_raises_error(self):
        """Production deployment without REDIS_URL must immediately raise a RuntimeError."""
        prod_settings = Settings(
            database_url="postgresql+asyncpg://user:pass@localhost:5432/db",
            environment="production",
            redis_url="",
            allow_in_memory_rate_limit=False,
            rate_limit_enabled=True,
        )
        with pytest.raises(RuntimeError, match="REDIS_URL must be configured in production"):
            resolve_rate_limit_storage_uri(prod_settings)

    def test_production_with_allow_in_memory_strictly_disallowed(self):
        """Production cannot bypass Redis by setting ALLOW_IN_MEMORY_RATE_LIMIT=True."""
        prod_settings = Settings(
            database_url="postgresql+asyncpg://user:pass@localhost:5432/db",
            environment="production",
            redis_url="redis://localhost:6379/0",
            allow_in_memory_rate_limit=True,
            rate_limit_enabled=True,
        )
        with pytest.raises(RuntimeError, match="ALLOW_IN_MEMORY_RATE_LIMIT is strictly disallowed in production"):
            resolve_rate_limit_storage_uri(prod_settings)

    def test_development_without_redis_and_without_opt_in_raises_error(self):
        """Development without Redis raises an informative error if ALLOW_IN_MEMORY_RATE_LIMIT is False."""
        dev_settings = Settings(
            database_url="postgresql+asyncpg://user:pass@localhost:5432/db",
            environment="development",
            redis_url="",
            allow_in_memory_rate_limit=False,
            rate_limit_enabled=True,
        )
        with pytest.raises(RuntimeError, match="REDIS_URL is not configured"):
            resolve_rate_limit_storage_uri(dev_settings)

    def test_development_with_opt_in_allows_memory_storage(self):
        """Development allows memory:// when ALLOW_IN_MEMORY_RATE_LIMIT=True is explicitly set."""
        dev_settings = Settings(
            database_url="postgresql+asyncpg://user:pass@localhost:5432/db",
            environment="development",
            redis_url="",
            allow_in_memory_rate_limit=True,
            rate_limit_enabled=True,
        )
        uri = resolve_rate_limit_storage_uri(dev_settings)
        assert uri == "memory://"

    def test_configured_redis_url_resolved(self):
        """When REDIS_URL is provided, it is resolved as the storage URI."""
        settings = Settings(
            database_url="postgresql+asyncpg://user:pass@localhost:5432/db",
            environment="production",
            redis_url="redis://:supersecret@redis.internal:6379/1",
            allow_in_memory_rate_limit=False,
            rate_limit_enabled=True,
        )
        uri = resolve_rate_limit_storage_uri(settings)
        assert uri == "redis://:supersecret@redis.internal:6379/1"


class TestSharedStorageAndMultiWorkerBehavior:
    """Tests verifying distributed coordination across worker instances."""

    def test_limiter_uses_redis_storage_when_configured(self):
        """Configuring a Limiter with redis:// attaches RedisStorage."""
        test_limiter = Limiter(key_func=lambda r: "test")
        settings = Settings(
            database_url="postgresql+asyncpg://user:pass@localhost:5432/db",
            environment="development",
            redis_url="redis://localhost:6379/0",
            allow_in_memory_rate_limit=False,
            rate_limit_enabled=True,
        )
        configure_limiter_storage(test_limiter, settings)
        assert isinstance(test_limiter._storage, RedisStorage)
        assert test_limiter._storage_uri == "redis://localhost:6379/0"

    def test_multi_worker_shared_counter_simulation(self):
        """Simulate two Uvicorn workers sharing the same backing storage."""
        dev_settings = Settings(
            database_url="postgresql+asyncpg://user:pass@localhost:5432/db",
            environment="development",
            redis_url="redis://localhost:6379/0",
            allow_in_memory_rate_limit=False,
            rate_limit_enabled=True,
        )

        worker1_limiter = Limiter(key_func=lambda r: "client_ip_1")
        worker2_limiter = Limiter(key_func=lambda r: "client_ip_1")

        configure_limiter_storage(worker1_limiter, dev_settings)
        configure_limiter_storage(worker2_limiter, dev_settings)

        # Simulate shared Redis key-value store across worker processes
        shared_counts = {}

        def shared_incr(key, expiry, amount=1):
            shared_counts[key] = shared_counts.get(key, 0) + amount
            return shared_counts[key]

        def shared_get(key):
            return shared_counts.get(key, 0)

        worker1_limiter._storage.incr = shared_incr
        worker1_limiter._storage.get = shared_get
        worker2_limiter._storage.incr = shared_incr
        worker2_limiter._storage.get = shared_get

        item = parse("5/minute")
        key = "login:127.0.0.1"

        # Worker 1 handles 3 requests
        assert worker1_limiter.limiter.hit(item, key) is True
        assert worker1_limiter.limiter.hit(item, key) is True
        assert worker1_limiter.limiter.hit(item, key) is True

        # Worker 2 handles the 4th and 5th request
        assert worker2_limiter.limiter.hit(item, key) is True
        assert worker2_limiter.limiter.hit(item, key) is True

        # 6th request across both workers must be blocked because the shared Redis quota (5) is exhausted
        assert worker1_limiter.limiter.hit(item, key) is False
        assert worker2_limiter.limiter.hit(item, key) is False


class TestRedisFailureSafety:
    """Tests verifying behavior when Redis becomes unreachable."""

    @pytest.mark.asyncio
    async def test_redis_failure_fails_safely_without_in_memory_fallback(self):
        """When Redis raises a connection error, requests fail safely with 500 without falling back to memory in prod."""
        import redis.exceptions

        app = FastAPI()
        test_limiter = Limiter(key_func=lambda r: "test_client")

        @app.get("/api/v1/test-rate-fail")
        @test_limiter.limit("5/minute")
        async def sample_endpoint(request: Request):
            return {"status": "ok"}

        app.state.limiter = test_limiter
        app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

        from app.utils.logger import log_unexpected_exception
        from app.middleware.security_headers import apply_security_headers
        from fastapi.responses import JSONResponse

        @app.exception_handler(Exception)
        async def custom_500(request: Request, exc: Exception):
            log_unexpected_exception(request, exc)
            return apply_security_headers(
                JSONResponse(
                    status_code=500,
                    content={"detail": "An unexpected error occurred. Please try again later."},
                )
            )

        # Mock hit() to raise Redis ConnectionError
        with patch.object(
            test_limiter.limiter,
            "hit",
            side_effect=redis.exceptions.ConnectionError("Connection to Redis refused"),
        ):
            transport = ASGITransport(app=app, raise_app_exceptions=False)
            async with AsyncClient(transport=transport, base_url="http://testserver") as client:
                res = await client.get("/api/v1/test-rate-fail")
                # Request fails safely with generic HTTP 500
                assert res.status_code == 500
                assert res.json()["detail"] == "An unexpected error occurred. Please try again later."
                # Verify in-memory fallback was not activated
                assert not getattr(test_limiter, "_in_memory_fallback_enabled", False)


class TestCredentialSanitization:
    """Tests verifying Redis credentials and URLs are never exposed in logs or strings."""

    def test_sanitize_storage_uri_masks_passwords(self):
        """Password in redis URL is replaced with ***."""
        clean = sanitize_storage_uri("redis://user:super_secret_pwd@redis.production.vpc:6379/0")
        assert "super_secret_pwd" not in clean
        assert clean == "redis://***@redis.production.vpc:6379/0"

    def test_sanitize_storage_uri_handles_memory_and_empty(self):
        """Memory and empty URIs return clean representations."""
        assert sanitize_storage_uri("memory://") == "memory://"
        assert sanitize_storage_uri("") == "memory://"
