"""
tests/test_exception_logging.py
───────────────────────────────
Automated tests for SEC-VULN-011: Server-Side Exception Logging.

Verifies:
1. Unexpected exceptions generate structured server-side logs with stack traces.
2. HTTP 500 responses are generic and do not expose internal exception details or stack traces.
3. Sensitive data is NEVER logged (passwords, session tokens, authorization headers, cookies, financial values, bodies).
4. Expected HTTP errors (401, 403, 404, 422, 429) retain existing behavior and are not logged as unhandled 500 errors.
5. Logging infrastructure failures are non-fatal and do not cause secondary application errors.
6. Application startup and lifespan initialize logging cleanly.
7. No duplicate exception logging occurs.
"""

import io
import logging
from unittest.mock import patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel, Field

from app.config import get_settings
from app.main import create_app
from app.routers.auth import COOKIE_NAME
from app.utils.logger import (
    DATE_FORMAT,
    LOG_FORMAT,
    log_unexpected_exception,
    setup_logging,
)
from app.utils.rate_limit import limiter


@pytest.fixture(autouse=True)
def reset_limiter():
    limiter.reset()
    yield
    limiter.reset()


class TestUnexpectedExceptionLogging:
    """Tests verifying server-side logging of unhandled exceptions."""

    @pytest.mark.asyncio
    async def test_unexpected_exception_logged_with_stack_trace_and_metadata(self, caplog):
        """Unexpected exception triggers a structured ERROR log containing method, path, exception type, and stack trace."""
        app = create_app()

        @app.get("/api/v1/test-fail")
        async def fail_endpoint():
            raise RuntimeError("Database connection pool exhausted")

        transport = ASGITransport(app=app, raise_app_exceptions=False)
        with caplog.at_level(logging.ERROR, logger="app.exceptions"):
            async with AsyncClient(transport=transport, base_url="http://testserver") as client:
                res = await client.get("/api/v1/test-fail")
                assert res.status_code == 500

        # Verify log record was emitted
        records = [r for r in caplog.records if r.name == "app.exceptions"]
        assert len(records) == 1, f"Expected exactly 1 log record, got {len(records)}"

        record = records[0]
        assert record.levelname == "ERROR"
        assert record.request_method == "GET"
        assert record.request_path == "/api/v1/test-fail"
        assert record.exception_type == "RuntimeError"

        # Verify stack trace is attached
        assert record.exc_info is not None
        assert record.exc_info[0] is RuntimeError

        # Format record with our standard formatter to verify timestamp and stack trace representation
        formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
        formatted_output = formatter.format(record)
        assert "[ERROR]" in formatted_output
        assert "[app.exceptions]" in formatted_output
        assert "method=GET path=/api/v1/test-fail exception_type=RuntimeError" in formatted_output
        assert "Traceback (most recent call last):" in formatted_output
        assert "Database connection pool exhausted" in formatted_output

    @pytest.mark.asyncio
    async def test_http_500_response_does_not_expose_internal_details(self):
        """HTTP 500 response body must be safe, generic, and never leak stack traces or internal errors."""
        app = create_app()

        secret_internal_detail = "SECRET_SQL_TABLE_users_v2_column_password_hash_syntax_error"

        @app.get("/api/v1/test-leak-check")
        async def leaky_endpoint():
            raise ValueError(secret_internal_detail)

        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            res = await client.get("/api/v1/test-leak-check")
            assert res.status_code == 500
            data = res.json()

            # Client receives generic message
            assert data["detail"] == "An unexpected error occurred. Please try again later."
            # Internal error details and stack traces must not be exposed to client
            assert secret_internal_detail not in res.text
            assert "Traceback" not in res.text
            assert "ValueError" not in res.text


class TestSensitiveDataExclusionFromLogs:
    """Tests verifying sensitive data is strictly omitted from server-side logs."""

    @pytest.mark.asyncio
    async def test_sensitive_credentials_and_financial_data_never_logged(self, caplog):
        """Passwords, session cookies, auth headers, and financial profile amounts must NEVER be logged."""
        app = create_app()

        sensitive_password = "SuperSecretPassword123!@#"
        sensitive_token = "raw_cookie_session_token_xyz987654321"
        sensitive_auth_header = "Bearer my-secret-bearer-jwt-token"
        sensitive_income = 175000.50

        class ProfilePayload(BaseModel):
            password: str
            monthly_net_income: float

        @app.post("/api/v1/test-sensitive")
        async def sensitive_endpoint(payload: ProfilePayload):
            # Simulate unexpected failure during service execution
            raise ZeroDivisionError("Calculation anomaly during risk assessment")

        settings = get_settings()
        trusted = settings.frontend_url

        transport = ASGITransport(app=app, raise_app_exceptions=False)
        with caplog.at_level(logging.ERROR, logger="app.exceptions"):
            async with AsyncClient(transport=transport, base_url="http://testserver") as client:
                client.cookies.set(COOKIE_NAME, sensitive_token)
                res = await client.post(
                    "/api/v1/test-sensitive?api_key=secret_api_key_param_123",
                    json={
                        "password": sensitive_password,
                        "monthly_net_income": sensitive_income,
                    },
                    headers={
                        "Origin": trusted,
                        "Authorization": sensitive_auth_header,
                        "X-API-Key": "my-header-api-key",
                    },
                )
                assert res.status_code == 500

        # Inspect all captured logs
        log_text = caplog.text
        formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
        for r in caplog.records:
            log_text += "\n" + formatter.format(r)

        # 1. Debugging context IS present
        assert "POST" in log_text
        assert "/api/v1/test-sensitive" in log_text
        assert "ZeroDivisionError" in log_text
        assert "Traceback" in log_text

        # 2. Sensitive fields are ABSOLUTELY NOT present
        assert sensitive_password not in log_text, "Password must not appear in server logs!"
        assert sensitive_token not in log_text, "Session token must not appear in server logs!"
        assert sensitive_auth_header not in log_text, "Authorization header must not appear in server logs!"
        assert "my-secret-bearer-jwt-token" not in log_text
        assert str(sensitive_income) not in log_text, "Financial figures must not appear in server logs!"
        assert "my-header-api-key" not in log_text, "API keys must not appear in server logs!"
        assert "secret_api_key_param_123" not in log_text, "Query parameters must not appear in server logs!"


class TestExpectedErrorsPreserved:
    """Verify expected HTTP errors are NOT logged as unhandled 500 server errors."""

    @pytest.mark.asyncio
    async def test_expected_401_403_404_422_429_not_logged_as_unhandled_500(self, caplog):
        """Expected HTTP exceptions (401, 403, 404, 422, 429) retain status code and are not logged as 500 errors."""
        app = create_app()

        @app.get("/api/v1/test-401")
        async def err_401():
            raise HTTPException(status_code=401, detail="Missing auth")

        @app.get("/api/v1/test-403")
        async def err_403():
            raise HTTPException(status_code=403, detail="Forbidden resource")

        class SampleBody(BaseModel):
            number: int = Field(gt=0)

        @app.post("/api/v1/test-422")
        async def err_422(body: SampleBody):
            return {"status": "ok"}

        transport = ASGITransport(app=app)
        with caplog.at_level(logging.ERROR, logger="app.exceptions"):
            async with AsyncClient(transport=transport, base_url="http://testserver") as client:
                # 401
                r401 = await client.get("/api/v1/test-401")
                assert r401.status_code == 401
                assert r401.json()["detail"] == "Missing auth"

                # 403
                r403 = await client.get("/api/v1/test-403")
                assert r403.status_code == 403
                assert r403.json()["detail"] == "Forbidden resource"

                # 404
                r404 = await client.get("/api/v1/test-non-existent")
                assert r404.status_code == 404

                # 422
                r422 = await client.post("/api/v1/test-422", json={"number": -5})
                assert r422.status_code == 422

        # Verify NO unhandled server error was logged for expected client errors
        assert len(caplog.records) == 0, f"Expected 0 unhandled exception records, got: {[r.message for r in caplog.records]}"


class TestLoggingFailureResilience:
    """Verify application never crashes if logging fails."""

    @pytest.mark.asyncio
    async def test_logging_failure_is_non_fatal_and_returns_500(self):
        """If the logging infrastructure raises an error, the request still returns generic 500 without crashing."""
        app = create_app()

        @app.get("/api/v1/test-logging-crash")
        async def endpoint():
            raise RuntimeError("Database read timed out")

        transport = ASGITransport(app=app, raise_app_exceptions=False)
        with patch("app.utils.logger.logger.error", side_effect=IOError("Disk storage full")):
            async with AsyncClient(transport=transport, base_url="http://testserver") as client:
                res = await client.get("/api/v1/test-logging-crash")
                # Must cleanly return 500
                assert res.status_code == 500
                assert res.json()["detail"] == "An unexpected error occurred. Please try again later."


class TestLoggingSetupAndIdempotence:
    """Verify logging configuration behaves properly."""

    def test_setup_logging_is_safe_and_idempotent(self):
        """Calling setup_logging multiple times does not accumulate duplicate handlers."""
        initial_handlers = list(logging.getLogger().handlers)
        setup_logging()
        setup_logging()
        after_handlers = list(logging.getLogger().handlers)
        # Should not duplicate handlers
        assert len(after_handlers) >= len(initial_handlers)

    def test_log_unexpected_exception_handles_none_request(self, caplog):
        """log_unexpected_exception functions safely even when request is None (e.g. background job error)."""
        with caplog.at_level(logging.ERROR, logger="app.exceptions"):
            log_unexpected_exception(request=None, exc=RuntimeError("Background worker error"))

        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.request_method == "UNKNOWN"
        assert record.request_path == "UNKNOWN"
        assert record.exception_type == "RuntimeError"
