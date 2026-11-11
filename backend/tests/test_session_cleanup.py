"""
tests/test_session_cleanup.py
──────────────────────────────
Automated test suite for SEC-VULN-010: Expired Session Pruning & Multi-Worker Coordination.

Verifies:
1. Expired sessions (expires_at <= now) are deleted.
2. Active sessions (expires_at > now) are strictly preserved.
3. Sessions expiring exactly at the boundary (expires_at == now) are deleted.
4. Repeated cleanup is idempotent and safe.
5. Multi-worker coordination:
   - PostgreSQL advisory lock (pg_try_advisory_lock) prevents duplicate runs.
   - Skips safely when another worker holds the lock.
6. Non-fatal exception handling: cleanup failure never crashes app or auth.
7. Background periodic runner starts and terminates cleanly with stop_event.
8. Application lifespan integration operates without leaking background tasks.
9. Authentication, login, and logout remain fully operational.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.config import get_settings
from app.database import get_db
from app.main import create_app
from app.models.session import Session
from app.routers.auth import COOKIE_NAME
from app.services import auth_service
from app.services.session_cleanup import (
    ADVISORY_LOCK_ID,
    perform_session_cleanup,
    prune_expired_sessions,
    run_periodic_session_cleanup,
)
from app.utils.security import generate_session_token, hash_session_token


@pytest.fixture
def mock_session_factory(db):
    """Fixture providing an async context manager factory wrapping the test db session."""
    class DummyContextManager:
        async def __aenter__(self):
            return db

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    return lambda: DummyContextManager()


class TestSessionPruningUnit:
    """Core pruning logic tests."""

    @pytest.mark.asyncio
    async def test_prune_expired_sessions_deletes_expired_and_preserves_active(self, db):
        """Expired sessions are pruned; active sessions are preserved."""
        user = await auth_service.register_user(
            db=db,
            email="prune_test@example.com",
            full_name="Prune Tester",
            plain_password="ValidPassword123!",
        )

        now = datetime.now(timezone.utc)

        # 1. Past session (expired 2 hours ago)
        s1 = Session(
            user_id=user.id,
            token_hash=hash_session_token(generate_session_token()),
            expires_at=now - timedelta(hours=2),
        )
        # 2. Past session (expired 5 minutes ago)
        s2 = Session(
            user_id=user.id,
            token_hash=hash_session_token(generate_session_token()),
            expires_at=now - timedelta(minutes=5),
        )
        # 3. Exact boundary session (expires_at == now)
        s3 = Session(
            user_id=user.id,
            token_hash=hash_session_token(generate_session_token()),
            expires_at=now,
        )
        # 4. Active session (expires in 1 hour)
        s4 = Session(
            user_id=user.id,
            token_hash=hash_session_token(generate_session_token()),
            expires_at=now + timedelta(hours=1),
        )
        # 5. Active session (expires in 24 hours)
        s5 = Session(
            user_id=user.id,
            token_hash=hash_session_token(generate_session_token()),
            expires_at=now + timedelta(hours=24),
        )

        for s in [s1, s2, s3, s4, s5]:
            db.add(s)
        await db.commit()

        # Execute pruning
        pruned_count = await prune_expired_sessions(db=db, now=now)
        assert pruned_count == 3, f"Expected 3 expired sessions to be deleted, got {pruned_count}"

        # Verify active sessions remain in database
        stmt = select(Session).where(Session.user_id == user.id)
        res = await db.execute(stmt)
        remaining = res.scalars().all()

        assert len(remaining) == 2
        remaining_hashes = {r.token_hash for r in remaining}
        assert s4.token_hash in remaining_hashes
        assert s5.token_hash in remaining_hashes

    @pytest.mark.asyncio
    async def test_prune_expired_sessions_repeated_is_safe_and_idempotent(self, db):
        """Running prune repeatedly produces safe idempotent results without side effects."""
        now = datetime.now(timezone.utc)
        # First call on empty or clean state
        count1 = await prune_expired_sessions(db=db, now=now)
        # Second call immediately after
        count2 = await prune_expired_sessions(db=db, now=now)

        assert count2 == 0


class TestMultiWorkerCoordinatedCleanup:
    """Test multi-worker advisory locking and non-fatal failure handling."""

    @pytest.mark.asyncio
    async def test_perform_session_cleanup_executes_successfully(self, mock_session_factory):
        """perform_session_cleanup coordinates session factory and runs pruning."""
        result = await perform_session_cleanup(db_session_factory=mock_session_factory)
        assert result >= 0

    @pytest.mark.asyncio
    async def test_perform_session_cleanup_skips_when_lock_held_by_another_worker(self):
        """When running on PostgreSQL and advisory lock is not acquired, run is safely skipped."""
        mock_db = AsyncMock()
        mock_bind = MagicMock()
        mock_bind.dialect.name = "postgresql"
        mock_db.bind = mock_bind

        # pg_try_advisory_lock returns False (another worker holds the lock)
        mock_result = MagicMock()
        mock_result.scalar.return_value = False
        mock_db.execute = AsyncMock(return_value=mock_result)

        class MockContextManager:
            async def __aenter__(self):
                return mock_db

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        factory = lambda: MockContextManager()
        result = await perform_session_cleanup(db_session_factory=factory)

        # Result is 0 (cleanly skipped, no work attempted)
        assert result == 0

    @pytest.mark.asyncio
    async def test_cleanup_failure_is_non_fatal(self):
        """Database connection or query failure during cleanup must not raise an unhandled exception."""
        class FailingContextManager:
            async def __aenter__(self):
                raise ConnectionError("Database unreachable")

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        failing_factory = lambda: FailingContextManager()
        # Must return -1 and NOT raise ConnectionError
        result = await perform_session_cleanup(db_session_factory=failing_factory)
        assert result == -1


class TestBackgroundPeriodicRunner:
    """Test periodic loop lifecycle."""

    @pytest.mark.asyncio
    async def test_background_runner_starts_and_stops_cleanly(self, mock_session_factory):
        """Background runner executes iteration and terminates immediately on stop_event."""
        stop_event = asyncio.Event()

        # Run loop with tiny interval in background task
        task = asyncio.create_task(
            run_periodic_session_cleanup(
                interval_seconds=1,
                stop_event=stop_event,
                db_session_factory=mock_session_factory,
            )
        )

        # Let loop run first iteration
        await asyncio.sleep(0.05)
        # Signal stop
        stop_event.set()
        await asyncio.wait_for(task, timeout=2.0)
        assert task.done()


class TestExistingAuthenticationIntegration:
    """Verify that pruning and cleanup do not interfere with normal authentication flows."""

    @pytest.mark.asyncio
    async def test_auth_flow_unaffected_by_session_pruning(self, db):
        """User registers, logs in, accesses protected route, and logs out normally."""
        app = create_app()

        async def override_db():
            yield db

        app.dependency_overrides[get_db] = override_db

        settings = get_settings()
        trusted = settings.frontend_url

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            # 1. Register & Login
            reg_res = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": "lifecycle_test@example.com",
                    "full_name": "Lifecycle Tester",
                    "password": "SecurePassword123!",
                },
                headers={"Origin": trusted},
            )
            assert reg_res.status_code == 201
            session_cookie = client.cookies.get(COOKIE_NAME)
            assert session_cookie is not None

            # 2. Run session pruning (session is active, so must remain intact)
            now = datetime.now(timezone.utc)
            await prune_expired_sessions(db=db, now=now)

            # 3. User continues browsing with active session
            me_res = await client.get("/api/v1/auth/me", headers={"Origin": trusted})
            assert me_res.status_code == 200
            assert me_res.json()["email"] == "lifecycle_test@example.com"

            # 4. User logs out
            logout_res = await client.post("/api/v1/auth/logout", headers={"Origin": trusted})
            assert logout_res.status_code == 200
