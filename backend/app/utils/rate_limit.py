"""
app/utils/rate_limit.py
───────────────────────
Rate limiting utility module using SlowAPI.

Provides:
- Secure client IP extraction resisting header spoofing unless behind trusted proxies.
- User-aware rate limit key function (falling back to client IP for unauthenticated calls).
- Global SlowAPI Limiter instance.
- Custom 429 exception handler with RFC-compliant Retry-After header and X-RateLimit headers.
"""

from ipaddress import IPv4Address, IPv6Address, ip_address
import math
import re
import time
from typing import Optional, Tuple, Union

from fastapi import Request
from fastapi.responses import JSONResponse
from limits.storage import storage_from_string
from limits.strategies import STRATEGIES
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded

from app.config import IPNetwork, Settings, get_settings, parse_trusted_proxy_networks
from app.middleware.auth_middleware import COOKIE_NAME
from app.utils.security import hash_session_token

IPAddress = Union[IPv4Address, IPv6Address]


def _parse_ip_address(raw_ip: str, *, allow_zone_id: bool = False) -> Optional[IPAddress]:
    """
    Parse and canonicalize a single IPv4 or IPv6 address string.

    Unwraps IPv4-mapped IPv6 addresses (e.g. ::ffff:10.0.0.1 -> 10.0.0.1) so dual-stack
    peers match IPv4 proxy CIDRs and share canonical rate-limit keys.
    Returns None for empty or malformed inputs.
    """
    candidate = raw_ip.strip()
    if not candidate:
        return None
    try:
        parsed = ip_address(candidate)
    except ValueError:
        return None
    if isinstance(parsed, IPv6Address):
        if not allow_zone_id and parsed.scope_id is not None:
            return None
        if parsed.ipv4_mapped is not None:
            return parsed.ipv4_mapped
    return parsed


def _is_trusted_proxy_ip(
    candidate_ip: IPAddress,
    trusted_networks: Tuple[IPNetwork, ...],
) -> bool:
    """Return True only if candidate_ip falls inside an explicitly trusted network."""
    return any(
        candidate_ip.version == network.version and candidate_ip in network
        for network in trusted_networks
    )


def get_client_ip(request: Request) -> str:
    """
    Safely extract the client IP address.

    Security rule (FIN-SEC-04):
    - Do NOT trust 'X-Forwarded-For' unless the immediate TCP peer (request.client.host)
      is explicitly covered by an IP or CIDR in settings.trusted_proxy_ips.
    - Walk X-Forwarded-For right-to-left, stripping trusted proxy hops, so spoofed
      left-hand entries sent by clients are ignored.
    - Safely ignore malformed, empty, or spoofed forwarded values and fall back to
      the canonical immediate connecting peer IP.
    """
    if not request.client or not request.client.host:
        return "127.0.0.1"

    raw_direct_ip = request.client.host
    peer_ip = _parse_ip_address(raw_direct_ip, allow_zone_id=True)
    if peer_ip is None:
        return raw_direct_ip.strip() or "127.0.0.1"

    canonical_peer = str(peer_ip)
    settings = get_settings()
    trusted_raw = getattr(settings, "trusted_proxy_ips", "") or ""
    trusted_networks = parse_trusted_proxy_networks(trusted_raw)

    if not trusted_networks or not _is_trusted_proxy_ip(peer_ip, trusted_networks):
        return canonical_peer

    forwarded_headers = request.headers.getlist("X-Forwarded-For")
    if not forwarded_headers:
        return canonical_peer

    forwarded_tokens = [
        token.strip()
        for header_val in forwarded_headers
        for token in header_val.split(",")
        if token.strip()
    ]
    if not forwarded_tokens:
        return canonical_peer

    earliest_trusted_ip: Optional[IPAddress] = None
    for token in reversed(forwarded_tokens):
        hop_ip = _parse_ip_address(token, allow_zone_id=False)
        if hop_ip is None:
            # Fail closed to the verified TCP peer if the right-hand chain contains
            # malformed or non-IP values before resolving an untrusted client IP.
            return canonical_peer
        if _is_trusted_proxy_ip(hop_ip, trusted_networks):
            earliest_trusted_ip = hop_ip
            continue
        return str(hop_ip)

    return str(earliest_trusted_ip) if earliest_trusted_ip is not None else canonical_peer


def get_user_or_ip_key(request: Request) -> str:
    """
    Generate rate-limit key for user-scoped endpoints (e.g. AI advisor chat).

    Priority:
    1. Authenticated user ID in request.state (populated by auth middleware).
    2. Session token cookie (if present before full auth resolution).
    3. Fallback to client IP for unauthenticated requests.
    """
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "id"):
        return f"user:{user.id}"

    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"

    session_cookie = request.cookies.get(COOKIE_NAME)
    if session_cookie:
        # Use short prefix of SHA-256 hash so raw token is never exposed in logs
        return f"token:{hash_session_token(session_cookie)[:16]}"

    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        bearer_token = auth_header[7:].strip()
        if bearer_token:
            return f"token:{hash_session_token(bearer_token)[:16]}"

    return f"ip:{get_client_ip(request)}"


def sanitize_storage_uri(uri: str) -> str:
    """Mask credentials in a storage URI for safe logging without credential exposure."""
    if not uri or uri.startswith("memory://"):
        return "memory://"
    return re.sub(r"://([^:@]+:)?([^@]+)@", r"://***@", uri)


def resolve_rate_limit_storage_uri(settings: Optional[Settings] = None) -> str:
    """
    Resolve the storage URI for SlowAPI distributed rate limiting (FIN-SEC-01).

    Rules:
    - If rate limiting is disabled, defaults to memory:// (no storage hit).
    - In production (is_production=True):
      * allow_in_memory_rate_limit is strictly disallowed.
      * redis_url is strictly required for multi-worker synchronization.
    - In non-production (development / test):
      * If redis_url is set, uses redis_url.
      * If allow_in_memory_rate_limit is True, uses memory://.
      * Otherwise, raises RuntimeError requiring either REDIS_URL or explicit ALLOW_IN_MEMORY_RATE_LIMIT=true.
    """
    if settings is None:
        settings = get_settings()

    if not settings.rate_limit_enabled:
        return "memory://"

    if settings.is_production:
        if settings.allow_in_memory_rate_limit:
            raise RuntimeError(
                "ALLOW_IN_MEMORY_RATE_LIMIT is strictly disallowed in production. "
                "Distributed storage (REDIS_URL) must be configured."
            )
        if not settings.redis_url or not settings.redis_url.strip():
            raise RuntimeError(
                "REDIS_URL must be configured in production to ensure distributed "
                "rate limiting across multiple workers."
            )
        return settings.redis_url.strip()

    # Non-production (development / test)
    if settings.redis_url and settings.redis_url.strip():
        return settings.redis_url.strip()

    if settings.allow_in_memory_rate_limit:
        return "memory://"

    raise RuntimeError(
        "REDIS_URL is not configured. For local development or testing without Redis, "
        "explicitly configure ALLOW_IN_MEMORY_RATE_LIMIT=true."
    )


def configure_limiter_storage(
    limiter_instance: Limiter, settings: Optional[Settings] = None
) -> None:
    """
    Attach the resolved storage backend (Redis or memory) to an existing Limiter instance.
    Never logs credentials or connection strings.
    """
    if settings is None:
        settings = get_settings()

    storage_uri = resolve_rate_limit_storage_uri(settings)
    storage = storage_from_string(storage_uri)

    limiter_instance._storage_uri = storage_uri
    limiter_instance._storage = storage

    strategy_name = limiter_instance._strategy or "fixed-window"
    strategy_cls = STRATEGIES[strategy_name]
    limiter_instance._limiter = strategy_cls(storage)
    limiter_instance.enabled = settings.rate_limit_enabled


# Centralized Limiter instance
settings = get_settings()
limiter = Limiter(
    key_func=get_client_ip,
    enabled=settings.rate_limit_enabled,
    storage_uri=resolve_rate_limit_storage_uri(settings),
)


def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    """
    Custom 429 response handler.
    Injects RFC-compliant Retry-After header and X-RateLimit status headers.
    """
    headers = {}
    current_limit = getattr(request.state, "view_rate_limit", None)

    reset_in_seconds = 60
    if current_limit:
        try:
            stats = limiter.limiter.get_window_stats(
                current_limit[0], *current_limit[1]
            )
            # stats[0] is epoch timestamp when current window resets
            reset_in_seconds = max(1, math.ceil(stats[0] - time.time()))
            headers["Retry-After"] = str(reset_in_seconds)
            headers["X-RateLimit-Limit"] = str(current_limit[0].amount)
            headers["X-RateLimit-Remaining"] = str(max(0, stats[1]))
            headers["X-RateLimit-Reset"] = str(int(stats[0]))
        except Exception:
            headers["Retry-After"] = str(reset_in_seconds)
    else:
        headers["Retry-After"] = str(reset_in_seconds)

    detail_message = f"Rate limit exceeded: {exc.detail}"
    response = JSONResponse(
        status_code=429,
        content={"detail": detail_message},
        headers=headers,
    )
    from app.middleware.security_headers import apply_security_headers

    return apply_security_headers(response)
