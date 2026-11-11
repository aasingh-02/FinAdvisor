"""
app/main.py
───────────
FastAPI application factory.

- Registers all routers under /api/v1
- Configures CORS to only allow the React frontend origin
- Sets up lifespan for startup / shutdown tasks
- Provides a global exception handler for unhandled errors
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings
from app.middleware.csrf_middleware import CSRFProtectionMiddleware
from app.middleware.security_headers import (
    SecurityHeadersMiddleware,
    apply_security_headers,
)
from app.utils.logger import log_unexpected_exception, setup_logging
from app.utils.rate_limit import limiter, rate_limit_exceeded_handler
from app.routers import auth as auth_router
from app.routers import profile as profile_router
from app.routers import emi as emi_router
from app.routers import foir as foir_router
from app.routers import risk as risk_router
from app.routers import recommendation as recommendation_router
from app.routers import dashboard as dashboard_router
from app.routers import advisor as advisor_router

settings = get_settings()


# ── Lifespan (startup / shutdown) ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Code before `yield` runs at startup.
    Code after `yield` runs at shutdown.
    DB table creation is handled by Alembic migrations — not here.
    """
    current_settings = get_settings()
    setup_logging()
    print(f"[STARTUP] FinAdvisor backend starting [{current_settings.environment}]")

    cleanup_task = None
    stop_event = None
    if current_settings.session_cleanup_enabled:
        from app.services.session_cleanup import run_periodic_session_cleanup

        stop_event = asyncio.Event()
        cleanup_task = asyncio.create_task(
            run_periodic_session_cleanup(
                interval_seconds=current_settings.session_cleanup_interval_seconds,
                stop_event=stop_event,
            )
        )

    try:
        yield
    finally:
        if stop_event and cleanup_task:
            stop_event.set()
            cleanup_task.cancel()
            try:
                await cleanup_task
            except (asyncio.CancelledError, Exception):
                pass
        print("[SHUTDOWN] FinAdvisor backend shutting down")


# ── App factory ───────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    setup_logging()
    settings = get_settings()

    # In production, disable interactive OpenAPI/Swagger/ReDoc documentation endpoints (SEC-VULN-005)
    docs_url = None if settings.is_production else "/docs"
    redoc_url = None if settings.is_production else "/redoc"
    openapi_url = None if settings.is_production else "/openapi.json"

    app = FastAPI(
        title="FinAdvisor API",
        description="AI-powered loan & EMI advisory platform — backend API.",
        version="1.0.0",
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
        lifespan=lifespan,
    )

    # ── CSRF Protection (Phase 6, SEC-VULN-006) ───────────────────────────────
    app.add_middleware(CSRFProtectionMiddleware)

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Allow only the React dev server (and production frontend URL).
    # `allow_credentials=True` is required for cookies to be sent cross-origin.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=True,  # Required for HTTP-only cookie auth
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Accept", "Authorization"],
    )

    # ── Security Headers (Phase 6, SEC-VULN-004) ──────────────────────────────
    app.add_middleware(SecurityHeadersMiddleware)

    # ── Rate Limiting (Phase 6 / FIN-SEC-01) ──────────────────────────────────
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    # ── Global exception handler (SEC-VULN-011) ───────────────────────────────
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """
        Catch-all for unexpected server errors.

        1. Preserves existing behavior for expected HTTP errors:
           - 401, 403, 404 (fastapi.HTTPException / StarletteHTTPException)
           - 422 (RequestValidationError)
           - 429 (RateLimitExceeded)
        2. Logs structured error details with stack trace to server-side logs.
        3. Returns a safe, generic HTTP 500 response without leaking stack traces or internal details.
        """
        # Preserve expected HTTP exceptions
        if isinstance(exc, (HTTPException, StarletteHTTPException)):
            return await http_exception_handler(request, exc)
        if isinstance(exc, RequestValidationError):
            return await request_validation_exception_handler(request, exc)
        if isinstance(exc, RateLimitExceeded):
            return rate_limit_exceeded_handler(request, exc)

        # Server-side structured exception logging (safe & non-fatal)
        try:
            log_unexpected_exception(request, exc)
        except Exception:
            pass

        # Generic safe client response
        response = JSONResponse(
            status_code=500,
            content={"detail": "An unexpected error occurred. Please try again later."},
        )
        return apply_security_headers(response)

    # ── Routers ───────────────────────────────────────────────────────────────
    API_PREFIX = "/api/v1"
    app.include_router(auth_router.router, prefix=API_PREFIX)
    app.include_router(profile_router.router, prefix=API_PREFIX)  # Financial Profile API
    app.include_router(emi_router.router, prefix=API_PREFIX)      # EMI Calculation Engine
    app.include_router(foir_router.router, prefix=API_PREFIX)     # FOIR Calculation Engine
    app.include_router(risk_router.router, prefix=API_PREFIX)     # Risk & Advisory Engine
    app.include_router(recommendation_router.router, prefix=API_PREFIX)  # Loan Recommendation Engine
    app.include_router(dashboard_router.router, prefix=API_PREFIX)       # Unified Dashboard & Health Score
    app.include_router(advisor_router.router, prefix=API_PREFIX)         # AI Advisor & Copilot Engine
    # Phase 2+ routers will be added here (profile, calculator, risk, etc.)

    # ── Health check ──────────────────────────────────────────────────────────
    @app.get("/health", tags=["Health"], summary="Health check")
    async def health_check():
        return {"status": "ok", "environment": settings.environment}

    # ── Documentation redirect (development only) ─────────────────────────────
    if not settings.is_production:
        @app.get("/api/docs", include_in_schema=False)
        async def redirect_api_docs():
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url="/docs")

    return app


app = create_app()
