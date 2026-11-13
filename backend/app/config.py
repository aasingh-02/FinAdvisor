"""
app/config.py
─────────────
Centralised settings loaded from the .env file.
All secrets and environment-specific values live here — never hard-coded.
"""

from functools import lru_cache
from ipaddress import IPv4Network, IPv6Network, ip_network
from pathlib import Path
from typing import Any, Optional, Tuple, Union

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

IPNetwork = Union[IPv4Network, IPv6Network]


def _parse_proxy_network(entry: str) -> IPNetwork:
    """Parse one TRUSTED_PROXY_IPS entry and forbid catch-all wildcard networks."""
    if entry in {"*", "all"}:
        raise ValueError(
            "Wildcard values (*, 0.0.0.0/0, ::/0) are forbidden in TRUSTED_PROXY_IPS."
        )
    network = ip_network(entry, strict=False)
    if network.prefixlen == 0:
        raise ValueError(
            "Catch-all CIDR ranges (0.0.0.0/0, ::/0) are forbidden in TRUSTED_PROXY_IPS."
        )
    return network


@lru_cache(maxsize=32)
def parse_trusted_proxy_networks(trusted_raw: str) -> Tuple[IPNetwork, ...]:
    """
    Parse comma-separated TRUSTED_PROXY_IPS into immutable IPv4/IPv6 network objects.

    Supports single IPv4/IPv6 addresses and CIDR ranges. Malformed entries and
    wildcard catch-all ranges (0.0.0.0/0, ::/0, *) are safely skipped at runtime.
    """
    networks: list[IPNetwork] = []
    for raw_entry in (trusted_raw or "").split(","):
        entry = raw_entry.strip()
        if not entry:
            continue
        try:
            networks.append(_parse_proxy_network(entry))
        except ValueError:
            continue
    return tuple(networks)


class Settings(BaseSettings):
    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str
    database_echo: bool = False

    # ── Session ───────────────────────────────────────────────────────────────
    session_expire_hours: int = 24
    session_cleanup_interval_seconds: int = 3600
    session_cleanup_enabled: bool = True
    # Optional explicit override for session cookie Secure flag (FIN-SEC-03).
    # Unset (None) defaults to True in production and False otherwise.
    cookie_secure_override: Optional[bool] = Field(
        default=None,
        alias="cookie_secure",
    )
    # Session cookie SameSite attribute: "lax", "strict", or "none" (default: "lax").
    # Use "none" for cross-origin split deployments (e.g. Vercel frontend + cloud backend).
    cookie_samesite: str = "lax"

    # ── Gemini (Phase 5) ──────────────────────────────────────────────────────
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"

    # ── Rate Limiting & Redis (Phase 6 / FIN-SEC-01) ──────────────────────────
    rate_limit_enabled: bool = True
    trusted_proxy_ips: str = ""
    redis_url: str = ""
    allow_in_memory_rate_limit: bool = False

    # ── App ───────────────────────────────────────────────────────────────────
    environment: str = "development"
    frontend_url: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=(_ENV_PATH, ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_database_url(cls, value: Any) -> Any:
        """Ensure PostgreSQL connection strings use the asyncpg dialect."""
        if isinstance(value, str):
            val = value.strip()
            if val.startswith("postgres://"):
                return "postgresql+asyncpg://" + val[len("postgres://"):]
            if val.startswith("postgresql://") and not val.startswith("postgresql+"):
                return "postgresql+asyncpg://" + val[len("postgresql://"):]
            return val
        return value

    @field_validator("database_echo", mode="before")
    @classmethod
    def _empty_database_echo_to_false(cls, value: Any) -> Any:
        """Treat blank DATABASE_ECHO environment values as False."""
        if isinstance(value, str) and not value.strip():
            return False
        return value

    @field_validator("cookie_secure_override", mode="before")
    @classmethod
    def _empty_cookie_secure_to_none(cls, value: Any) -> Any:
        """Treat blank COOKIE_SECURE environment values as unset (None)."""
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("cookie_samesite", mode="before")
    @classmethod
    def _validate_cookie_samesite(cls, value: Any) -> str:
        """Validate COOKIE_SAMESITE against RFC 6265bis allowed values."""
        if value is None or (isinstance(value, str) and not value.strip()):
            return "lax"
        s = str(value).strip().lower()
        if s not in {"lax", "strict", "none"}:
            raise ValueError(
                f"Invalid COOKIE_SAMESITE '{value}'. Allowed values are 'lax', 'strict', or 'none'."
            )
        return s

    @field_validator("trusted_proxy_ips")
    @classmethod
    def _validate_trusted_proxy_ips(cls, value: str) -> str:
        """Validate configured TRUSTED_PROXY_IPS entries and reject wildcards."""
        for raw_entry in (value or "").split(","):
            entry = raw_entry.strip()
            if entry:
                _parse_proxy_network(entry)
        return value

    @model_validator(mode="after")
    def _enforce_production_security_settings(self) -> "Settings":
        """Enforce production security invariants for cookies and SQL logging."""
        if self.is_production and self.cookie_secure_override is False:
            raise ValueError(
                "COOKIE_SECURE cannot be set to false in production. "
                "Production must always enforce Secure=True on session cookies."
            )
        if self.cookie_samesite == "none" and not self.cookie_secure:
            raise ValueError(
                "COOKIE_SAMESITE cannot be 'none' when cookie_secure is False. "
                "Modern browsers strictly reject SameSite=None cookies unless Secure=True (HTTPS)."
            )
        if self.is_production and self.database_echo:
            self.database_echo = False
        return self

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() == "production"

    @property
    def effective_database_echo(self) -> bool:
        """
        Effective SQLAlchemy SQL echo setting (FIN-SEC-05).

        Always False in production even if DATABASE_ECHO=true is supplied;
        in non-production environments, defaults to False unless DATABASE_ECHO=true.
        """
        if self.is_production:
            return False
        return bool(self.database_echo)

    @property
    def cookie_secure(self) -> bool:
        """
        Effective Secure flag for session cookies.

        - In production: always True (cannot be disabled).
        - Outside production: uses COOKIE_SECURE if explicitly set, else False.
        """
        if self.is_production:
            return True
        if self.cookie_secure_override is not None:
            return self.cookie_secure_override
        return False


@lru_cache
def get_settings() -> Settings:
    """Cached singleton — called via FastAPI Depends(get_settings)."""
    return Settings()
