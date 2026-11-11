"""
app/database.py
───────────────
Async SQLAlchemy engine + session factory.

Usage inside a route/service:
    async with get_db() as db:
        result = await db.execute(...)
"""

from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import Settings, get_settings

settings = get_settings()


def create_database_engine(custom_settings: Optional[Settings] = None) -> AsyncEngine:
    """
    Create the configured async SQLAlchemy engine (FIN-SEC-05).

    - SQL echo defaults to False (DATABASE_ECHO=false) and is strictly forced to
      False in production even if DATABASE_ECHO=true is set.
    - echo_pool is explicitly False to avoid connection/pool debug leakage.
    - hide_parameters=True prevents bound SQL parameters (passwords, tokens, hashes,
      financial amounts) from ever appearing in SQL logs or error strings.
    """
    active_settings = custom_settings or get_settings()
    return create_async_engine(
        active_settings.database_url,
        echo=active_settings.effective_database_echo,
        echo_pool=False,
        hide_parameters=True,
        pool_pre_ping=True,                          # Detect stale connections
        pool_size=10,
        max_overflow=20,
    )


# ── Engine ────────────────────────────────────────────────────────────────────
engine = create_database_engine(settings)

# ── Session factory ───────────────────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ── Base class for all ORM models ─────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── FastAPI dependency ────────────────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async DB session; commit on success, rollback on error."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
