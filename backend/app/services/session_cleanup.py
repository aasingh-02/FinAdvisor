"""
app/services/session_cleanup.py
───────────────────────────────
Expired session cleanup service (SEC-VULN-010).

Features:
- Deletes sessions where expires_at <= now (preserves active sessions).
- PostgreSQL advisory locking (pg_try_advisory_lock) prevents duplicate concurrent
  runs across multiple application worker processes.
- Safe fallback for non-PostgreSQL databases (e.g. SQLite during automated testing).
- Non-fatal exception handling: failures never interrupt user requests or startup.
- Safe logging: zero exposure of session tokens, hashes, user IDs, or passwords.
"""

import asyncio
from datetime import datetime, timezone
import logging
from typing import Callable, Optional

from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.session import Session

logger = logging.getLogger(__name__)

# Fixed 64-bit integer identifier for PostgreSQL advisory lock
ADVISORY_LOCK_ID = 1048576


async def prune_expired_sessions(
    db: AsyncSession,
    now: Optional[datetime] = None,
) -> int:
    """
    Delete expired session records from the database.

    A session is considered expired if its `expires_at` timestamp is strictly
    less than or equal to `now` (default: current UTC time).
    Active sessions (`expires_at > now`) are strictly preserved.

    Returns:
        int: Number of deleted expired session rows.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    stmt = delete(Session).where(Session.expires_at <= now)
    result = await db.execute(stmt)
    await db.commit()

    count = result.rowcount if result.rowcount is not None and result.rowcount >= 0 else 0
    return count


async def perform_session_cleanup(
    db_session_factory: Callable[[], AsyncSession] = AsyncSessionLocal,
    now: Optional[datetime] = None,
) -> int:
    """
    Execute a coordinated session cleanup run with multi-worker concurrency protection.

    When running on PostgreSQL, acquires an advisory lock (pg_try_advisory_lock) so that
    only ONE worker executes the cleanup if multiple Uvicorn workers wake up simultaneously.
    If the lock is held by another worker, execution is safely skipped.

    All errors are caught and logged as non-fatal warnings to ensure that cleanup
    issues never degrade application availability.

    Returns:
        int: Number of deleted sessions (>= 0), or -1 if an error occurred.
    """
    try:
        async with db_session_factory() as db:
            is_postgres = False
            lock_acquired = False

            # Check if running against a PostgreSQL dialect
            bind = getattr(db, "bind", None)
            if bind is None:
                sync_sess = getattr(db, "_sync_sess", None)
                if sync_sess is not None:
                    bind = getattr(sync_sess, "bind", None)

            if bind and hasattr(bind, "dialect") and bind.dialect.name == "postgresql":
                is_postgres = True

            if is_postgres:
                # Attempt to acquire advisory lock without blocking
                try:
                    res = await db.execute(
                        text("SELECT pg_try_advisory_lock(:key)"),
                        {"key": ADVISORY_LOCK_ID},
                    )
                    lock_acquired = bool(res.scalar())
                except Exception as lock_err:
                    logger.warning(
                        f"[SESSION_CLEANUP] Failed to acquire advisory lock: {lock_err}"
                    )
                    lock_acquired = False

                if not lock_acquired:
                    logger.info(
                        "[SESSION_CLEANUP] Another worker currently holds the cleanup lock. Skipping run."
                    )
                    return 0

            try:
                # Perform atomic deletion
                pruned = await prune_expired_sessions(db=db, now=now)
                if pruned > 0:
                    logger.info(f"[SESSION_CLEANUP] Pruned {pruned} expired session(s).")
                else:
                    logger.debug("[SESSION_CLEANUP] No expired sessions to prune.")
                return pruned
            finally:
                if is_postgres and lock_acquired:
                    try:
                        await db.execute(
                            text("SELECT pg_advisory_unlock(:key)"),
                            {"key": ADVISORY_LOCK_ID},
                        )
                    except Exception as unlock_err:
                        logger.warning(
                            f"[SESSION_CLEANUP] Failed to release advisory lock: {unlock_err}"
                        )
    except Exception as exc:
        logger.warning(f"[SESSION_CLEANUP] Session cleanup encountered an error (non-fatal): {exc}")
        return -1


async def run_periodic_session_cleanup(
    interval_seconds: int = 3600,
    stop_event: Optional[asyncio.Event] = None,
    db_session_factory: Callable[[], AsyncSession] = AsyncSessionLocal,
) -> None:
    """
    Background loop that periodically executes session cleanup.

    Terminates cleanly when `stop_event` is set or the task is cancelled.
    """
    logger.info(
        f"[SESSION_CLEANUP] Background cleaner loop started (interval: {interval_seconds}s)"
    )
    while True:
        if stop_event and stop_event.is_set():
            break

        await perform_session_cleanup(db_session_factory=db_session_factory)

        try:
            if stop_event:
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=max(1, interval_seconds))
                    break  # Stop event was signalled
                except asyncio.TimeoutError:
                    pass  # Interval elapsed, proceed to next iteration
            else:
                await asyncio.sleep(max(1, interval_seconds))
        except asyncio.CancelledError:
            break

    logger.info("[SESSION_CLEANUP] Background cleaner loop stopped.")
