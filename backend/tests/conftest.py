"""
tests/conftest.py
─────────────────
Shared pytest fixtures.

Uses SQLite (synchronous driver, no aiosqlite needed) wrapped with
SQLAlchemy's run_sync so async service functions work without change.
No live PostgreSQL required.
"""

import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session

from app.database import Base

# Import models so SQLAlchemy registers them with Base.metadata
import app.models.user               # noqa: F401
import app.models.session            # noqa: F401
import app.models.financial_profile  # noqa: F401

# ── Sync SQLite engine for schema creation ────────────────────────────────────
# We use a file-based SQLite DB in /tmp so it persists for the test session
# but is wiped at the end. aiosqlite is NOT required.
SYNC_DB_URL = "sqlite:///./test_finadvisor.db"

sync_engine = create_engine(
    SYNC_DB_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)


@pytest.fixture(scope="session", autouse=True)
def create_tables():
    """Create all tables once at session start; drop them afterwards."""
    Base.metadata.create_all(sync_engine)
    yield
    Base.metadata.drop_all(sync_engine)
    sync_engine.dispose()
    # Clean up the file
    import os
    try:
        os.remove("./test_finadvisor.db")
    except FileNotFoundError:
        pass


@pytest.fixture
def db() -> AsyncSession:
    """
    Provide an AsyncSession backed by a synchronous SQLite connection.

    Each test gets a fresh connection; changes are rolled back at the end
    so tests stay fully isolated.

    We use SQLAlchemy's AsyncSession in 'autobegin' mode over a sync
    connection — this avoids any need for aiosqlite.
    """
    from sqlalchemy.ext.asyncio import AsyncSession as _AsyncSession
    from sqlalchemy.orm import sessionmaker

    # Open a sync connection, begin a transaction
    conn = sync_engine.connect()
    trans = conn.begin()

    # Wrap the sync connection in an AsyncSession so services see the
    # same interface as production (AsyncSession).  Using the
    # 'sync_session' bridge provided by SQLAlchemy.
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import Session as SyncSession

    sync_session = SyncSession(bind=conn, expire_on_commit=False, autoflush=False)

    # Monkeypatch: return a thin wrapper that delegates all async calls to sync
    class _SyncBridgeSession(AsyncSession):
        """
        Wraps a synchronous Session so that async service code (which awaits
        execute / flush / etc.) works against a plain sync SQLite connection.
        """

        def __init__(self, sync_sess: SyncSession):
            # Do NOT call super().__init__() — we're monkey-patching
            self._sync_sess = sync_sess

        # ── Core async methods bridged to sync ────────────────────────────────

        async def execute(self, statement, *args, **kwargs):
            return self._sync_sess.execute(statement, *args, **kwargs)

        async def flush(self, objects=None):
            self._sync_sess.flush(objects)

        async def commit(self):
            self._sync_sess.flush()  # don't actually commit — rollback in teardown

        async def rollback(self):
            self._sync_sess.rollback()

        def add(self, instance, _warn=True):
            self._sync_sess.add(instance)

        async def delete(self, instance):
            self._sync_sess.delete(instance)

        async def refresh(self, instance, attribute_names=None, with_for_update=None):
            self._sync_sess.refresh(instance)

        async def get(self, entity, ident, **kwargs):
            return self._sync_sess.get(entity, ident, **kwargs)

        # ── Support `async with session:` ─────────────────────────────────────

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass  # teardown happens in the fixture

    session = _SyncBridgeSession(sync_session)
    yield session

    # Teardown: roll back everything the test wrote
    sync_session.close()
    trans.rollback()
    conn.close()
