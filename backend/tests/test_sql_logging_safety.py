"""
tests/test_sql_logging_safety.py
────────────────────────────────
Automated tests for FIN-SEC-05: SQL Statement Logging Safety Review.

Verifies:
1. Development defaults to DATABASE_ECHO=False (no accidental SQL statement echo).
2. Development supports explicitly enabling DATABASE_ECHO=true.
3. Production defaults to echo=False and hides bound parameters.
4. Production always forces SQL echo to False even if DATABASE_ECHO=true is supplied.
5. Engine hide_parameters=True guarantees sensitive bound values (passwords,
   session tokens, token hashes, Redis credentials, financial amounts) never
   appear in SQL logs or SQLAlchemy exception strings.
"""

import io
import logging

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from app.config import Settings, get_settings
from app.database import create_database_engine, engine as app_engine
from app.utils.logger import setup_logging

_TEST_DB_URL = "postgresql+asyncpg://user:db_pass_secret@localhost:5432/finadvisor_test"


@pytest.fixture
def isolated_sqlalchemy_engine_logger():
    """Capture sqlalchemy.engine logs cleanly and restore original logger state."""
    engine_logger = logging.getLogger("sqlalchemy.engine")
    inner_engine_logger = logging.getLogger("sqlalchemy.engine.Engine")
    orig_level = engine_logger.level
    orig_inner_level = inner_engine_logger.level
    orig_handlers = list(engine_logger.handlers)
    orig_inner_handlers = list(inner_engine_logger.handlers)

    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    engine_logger.addHandler(handler)

    try:
        yield stream
    finally:
        engine_logger.removeHandler(handler)
        engine_logger.setLevel(orig_level)
        inner_engine_logger.setLevel(orig_inner_level)
        engine_logger.handlers[:] = orig_handlers
        inner_engine_logger.handlers[:] = orig_inner_handlers


class TestDatabaseEchoConfiguration:
    @pytest.mark.asyncio
    async def test_development_defaults_to_database_echo_false(self, monkeypatch):
        """Development without DATABASE_ECHO defaults to SQL echo=False and hides parameters."""
        monkeypatch.delenv("DATABASE_ECHO", raising=False)
        monkeypatch.delenv("ENVIRONMENT", raising=False)

        cfg = Settings(database_url=_TEST_DB_URL, environment="development", _env_file=None)
        assert cfg.is_production is False
        assert cfg.database_echo is False
        assert cfg.effective_database_echo is False

        engine = create_database_engine(cfg)
        try:
            assert engine.echo is False
            assert engine.sync_engine.pool.echo is False
            assert engine.sync_engine.hide_parameters is True
        finally:
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_development_supports_explicit_database_echo_true(self, monkeypatch):
        """Development allows opting into SQL echo via DATABASE_ECHO=true while hiding params."""
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("DATABASE_ECHO", "true")

        cfg = Settings(database_url=_TEST_DB_URL, _env_file=None)
        assert cfg.is_production is False
        assert cfg.database_echo is True
        assert cfg.effective_database_echo is True

        engine = create_database_engine(cfg)
        try:
            assert engine.echo is True
            assert engine.sync_engine.pool.echo is False
            assert engine.sync_engine.hide_parameters is True
        finally:
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_production_defaults_to_database_echo_false(self, monkeypatch):
        """Production defaults to echo=False and hide_parameters=True."""
        monkeypatch.delenv("DATABASE_ECHO", raising=False)

        cfg = Settings(database_url=_TEST_DB_URL, environment="production", _env_file=None)
        assert cfg.is_production is True
        assert cfg.database_echo is False
        assert cfg.effective_database_echo is False

        engine = create_database_engine(cfg)
        try:
            assert engine.echo is False
            assert engine.sync_engine.pool.echo is False
            assert engine.sync_engine.hide_parameters is True
        finally:
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_production_forces_sql_echo_false_even_when_database_echo_true(self, monkeypatch):
        """
        Production MUST force SQL echo to False even if DATABASE_ECHO=true is supplied
        via environment variables, init kwargs, or runtime mutation.
        """
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("DATABASE_ECHO", "true")

        cfg_from_env = Settings(database_url=_TEST_DB_URL, _env_file=None)
        assert cfg_from_env.is_production is True
        assert cfg_from_env.database_echo is False
        assert cfg_from_env.effective_database_echo is False

        cfg_from_init = Settings(
            database_url=_TEST_DB_URL,
            environment="production",
            database_echo=True,
            _env_file=None,
        )
        assert cfg_from_init.database_echo is False
        assert cfg_from_init.effective_database_echo is False

        # Runtime mutation defense-in-depth
        settings = get_settings()
        monkeypatch.setattr(settings, "environment", "production")
        monkeypatch.setattr(settings, "database_echo", True)
        assert settings.effective_database_echo is False

        engine = create_database_engine(settings)
        try:
            assert engine.echo is False
            assert engine.sync_engine.hide_parameters is True
        finally:
            await engine.dispose()

    def test_blank_database_echo_env_defaults_to_false(self, monkeypatch):
        """Empty DATABASE_ECHO= string cleanly resolves to False without validation failure."""
        monkeypatch.setenv("DATABASE_ECHO", "   ")
        cfg = Settings(database_url=_TEST_DB_URL, environment="development", _env_file=None)
        assert cfg.database_echo is False
        assert cfg.effective_database_echo is False

    def test_module_engine_disables_pool_echo_and_hides_parameters(self):
        """Application default engine enforces safe logging attributes."""
        assert app_engine.sync_engine.pool.echo is False
        assert app_engine.sync_engine.hide_parameters is True


class TestSqlParameterRedactionAndSilence:
    def test_production_emits_no_sql_logs_and_hides_sensitive_parameters(
        self, isolated_sqlalchemy_engine_logger
    ):
        """
        In production, setup_logging() + production engine emits zero SQL logs
        and redacts all sensitive bind values even on SQLAlchemy exceptions.
        """
        setup_logging(level=logging.INFO)
        prod_cfg = Settings(
            database_url=_TEST_DB_URL,
            environment="production",
            database_echo=True,  # must be overridden to False
            _env_file=None,
        )

        # Mirror production engine settings on an executable in-memory sync engine
        sync_prod = create_engine(
            "sqlite:///:memory:",
            echo=prod_cfg.effective_database_echo,
            echo_pool=False,
            hide_parameters=app_engine.sync_engine.hide_parameters,
        )

        sensitive_values = [
            "SuperSecretPassword!99",
            "raw_session_token_abc123",
            "sha256_token_hash_deadbeef",
            "redis://:redis_secret@redis:6379/0",
            "987654.32",
        ]

        try:
            with sync_prod.begin() as conn:
                conn.execute(text("CREATE TABLE audit_check (id INTEGER PRIMARY KEY, val TEXT)"))
                for idx, secret in enumerate(sensitive_values, start=1):
                    conn.execute(
                        text("INSERT INTO audit_check (id, val) VALUES (:id, :val)"),
                        {"id": idx, "val": secret},
                    )

            # No SQL statements or parameters emitted in production
            captured = isolated_sqlalchemy_engine_logger.getvalue()
            assert captured == ""

            # Even if an unexpected IntegrityError occurs, bound values remain redacted
            with pytest.raises(IntegrityError) as exc_info:
                with sync_prod.begin() as conn:
                    conn.execute(
                        text("INSERT INTO audit_check (id, val) VALUES (:id, :val)"),
                        {"id": 1, "val": "SuperSecretPassword!99"},
                    )
            exc_text = str(exc_info.value)
            assert "SQL parameters hidden due to hide_parameters=True" in exc_text
            assert "SuperSecretPassword!99" not in exc_text
        finally:
            sync_prod.dispose()

    def test_dev_echo_logs_sql_structure_without_exposing_sensitive_parameters(
        self, isolated_sqlalchemy_engine_logger
    ):
        """
        When DATABASE_ECHO=true in development, SQL structure may be logged while
        bound parameters (passwords, hashes, financial values) remain hidden.
        """
        dev_cfg = Settings(
            database_url=_TEST_DB_URL,
            environment="development",
            database_echo=True,
            _env_file=None,
        )

        sync_dev = create_engine(
            "sqlite:///:memory:",
            echo=dev_cfg.effective_database_echo,
            echo_pool=False,
            hide_parameters=app_engine.sync_engine.hide_parameters,
        )

        try:
            with sync_dev.begin() as conn:
                conn.execute(text("CREATE TABLE user_check (email TEXT, secret TEXT, income NUMERIC)"))
                conn.execute(
                    text("INSERT INTO user_check VALUES (:email, :secret, :income)"),
                    {
                        "email": "user@example.com",
                        "secret": "bcrypt_secret_hash_xyz",
                        "income": 456789.12,
                    },
                )

            log_output = isolated_sqlalchemy_engine_logger.getvalue()
            assert "INSERT INTO user_check" in log_output
            assert "SQL parameters hidden due to hide_parameters=True" in log_output
            assert "bcrypt_secret_hash_xyz" not in log_output
            assert "456789.12" not in log_output
        finally:
            sync_dev.dispose()
