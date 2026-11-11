"""
app/middleware/security_headers.py
───────────────────────────────────
Middleware and utilities to enforce standard HTTP security headers across all API responses.

Headers applied:
1. X-Content-Type-Options: nosniff
   Prevents MIME-sniffing vulnerabilities.
2. X-Frame-Options: DENY
   Protects against clickjacking and UI redress attacks.
3. Referrer-Policy: strict-origin-when-cross-origin
   Protects referrer metadata across origins.
4. Content-Security-Policy (CSP):
   - Development: Allows Swagger UI/ReDoc CDN assets and inline init scripts on /docs & /redoc.
   - Production: Strict API-only policy (default-src 'none') since /docs & /redoc are disabled,
     preserving frame-ancestors 'none' and object-src 'none' without weakening script/style rules.
   Note: For a separately hosted React SPA, the frontend web server / CDN serving index.html
   must configure the frontend document CSP (see frontend/csp.js and frontend/vite.config.js).
5. Strict-Transport-Security (HSTS):
   Enforced ONLY in production behind HTTPS (max-age=31536000; includeSubDomains).
"""

from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import Settings, get_settings

# Development backend CSP (supports interactive Swagger UI / ReDoc at /docs & /redoc)
CSP_POLICY = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "img-src 'self' data: https:; "
    "font-src 'self' data: https:; "
    "connect-src 'self'; "
    "object-src 'none'; "
    "frame-ancestors 'none';"
)

# Production backend CSP (JSON API responses only — /docs and /redoc are disabled)
PROD_API_CSP_POLICY = (
    "default-src 'none'; "
    "connect-src 'self'; "
    "object-src 'none'; "
    "base-uri 'none'; "
    "frame-ancestors 'none';"
)


def get_backend_csp_policy(settings: Optional[Settings] = None) -> str:
    """Return the environment-appropriate CSP for backend FastAPI responses."""
    if settings is None:
        settings = get_settings()
    if settings.is_production:
        return PROD_API_CSP_POLICY
    return CSP_POLICY


def apply_security_headers(response: Response) -> Response:
    """
    Attach standard HTTP security headers to any Starlette/FastAPI Response.
    Used by middleware as well as dedicated exception handlers (e.g. 429, 500).
    """
    settings = get_settings()

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = get_backend_csp_policy(settings)

    if settings.is_production:
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

    return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    HTTP middleware wrapping all responses passing through FastAPI.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        return apply_security_headers(response)
