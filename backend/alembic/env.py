"""
alembic/env.py
──────────────
Alembic async migration environment.

Reads DATABASE_URL from .env via app.config so migrations always use the
same connection string as the application — no duplication.
"""

import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

# Add backend directory to sys.path so app can always be imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# ── Import app components ─────────────────────────────────────────────────────
# Models must be imported so Alembic can discover their metadata.
from app.config import get_settings
from app.database import Base
import app.models.user               # noqa: F401 — registers User with Base.metadata
import app.models.session            # noqa: F401 — registers Session with Base.metadata
import app.models.financial_profile  # noqa: F401 — registers FinancialProfile with Base.metadata

settings = get_settings()

# ── Alembic Config object ─────────────────────────────────────────────────────
config = context.config

# Override sqlalchemy.url with the value from .env
config.set_main_option("sqlalchemy.url", settings.database_url)

# Interpret alembic.ini's logging config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate
target_metadata = Base.metadata


# ── Offline mode (generates SQL without a live DB) ───────────────────────────

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online mode (runs against a live DB) ──────────────────────────────────────

def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = settings.database_url
    configuration["sqlalchemy.echo"] = "false"
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        hide_parameters=True,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


# ── Entry point ───────────────────────────────────────────────────────────────

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
