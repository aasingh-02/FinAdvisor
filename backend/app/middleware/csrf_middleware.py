"""
app/middleware/csrf_middleware.py
─────────────────────────────────
Defense-in-depth CSRF (Cross-Site Request Forgery) protection middleware.

Hardened Security Policy & Browser Protections:
1. Safe methods (GET, HEAD, OPTIONS) are exempt from CSRF checks.
2. State-changing methods (POST, PUT, PATCH, DELETE) require strict validation:
   a. If 'Origin' header is present:
      - Normalized (scheme + host:port) and strictly validated against
        configured settings.frontend_url.
      - Any untrusted Origin is immediately rejected with HTTP 403 Forbidden.
   b. Else if 'Referer' header is present (Origin absent):
      - Origin component extracted and strictly validated against
        settings.frontend_url.
      - Any untrusted Referer is immediately rejected with HTTP 403 Forbidden.
   c. If both 'Origin' and 'Referer' are absent:
      - Authenticated browser requests (carrying the 'session_token' cookie)
        are STRICTLY REJECTED with HTTP 403 Forbidden.
        Rationale: Browsers in legitimate operation always provide Origin or Referer
        headers on state-changing requests. A cookie-authenticated request omitting both
        is a potential CSRF vector (e.g. proxy stripping, referrer-policy abuse, or crafted exploit).
      - Unauthenticated requests (e.g. login/register before session cookie is established)
        or non-browser API clients using explicit token authentication (e.g. Authorization header)
        are permitted to proceed to downstream handlers.
"""

from typing import Set
from urllib.parse import urlparse

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import get_settings
from app.middleware.auth_middleware import COOKIE_NAME
from app.middleware.security_headers import apply_security_headers


def normalize_origin(url: str) -> str:
    """
    Extract and normalize the scheme and host:port from an Origin or Referer URL.
    Returns lowercase 'scheme://host:port' without trailing slashes.
    """
    if not url:
        return ""
    cleaned = url.strip()
    parsed = urlparse(cleaned)
    if not parsed.scheme or not parsed.netloc:
        return cleaned.rstrip("/").lower()
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"


def get_trusted_origins() -> Set[str]:
    """
    Retrieve normalized set of trusted origins from settings.frontend_url.
    Supports comma-separated origins.
    """
    settings = get_settings()
    raw = getattr(settings, "frontend_url", "") or ""
    return {normalize_origin(origin) for origin in raw.split(",") if origin.strip()}


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """
    Middleware that verifies Origin and Referer headers on state-changing requests
    to prevent Cross-Site Request Forgery (CSRF).
    """

    SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

    async def dispatch(self, request: Request, call_next) -> Response:
        # 1. Skip safe/idempotent methods and CORS preflight
        if request.method in self.SAFE_METHODS:
            return await call_next(request)

        trusted_origins = get_trusted_origins()

        origin_header = request.headers.get("origin")
        referer_header = request.headers.get("referer")

        # 2. Check Origin header if present
        if origin_header:
            req_origin = normalize_origin(origin_header)
            if req_origin not in trusted_origins:
                err_response = JSONResponse(
                    status_code=403,
                    content={"detail": "CSRF verification failed: Untrusted Origin."},
                )
                return apply_security_headers(err_response)

        # 3. Fallback to Referer header if Origin is absent
        elif referer_header:
            ref_origin = normalize_origin(referer_header)
            if ref_origin not in trusted_origins:
                err_response = JSONResponse(
                    status_code=403,
                    content={"detail": "CSRF verification failed: Untrusted Referer."},
                )
                return apply_security_headers(err_response)

        # 4. If both Origin and Referer are absent:
        # Reject state-changing requests when using cookie-based browser authentication
        elif request.cookies.get(COOKIE_NAME):
            err_response = JSONResponse(
                status_code=403,
                content={
                    "detail": "CSRF verification failed: Missing Origin and Referer on cookie-authenticated request."
                },
            )
            return apply_security_headers(err_response)

        # 5. Allow unauthenticated or non-cookie requests (handled by downstream auth guards)
        return await call_next(request)
