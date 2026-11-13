"""
app/routers/auth.py
────────────────────
HTTP layer for authentication endpoints.

Responsibilities:
- Parse / validate HTTP request (via Pydantic schemas)
- Call auth_service functions (business logic)
- Set / clear the HTTP-only session cookie
- Return appropriate HTTP responses

Business logic (hashing, DB queries) stays in services/.
"""

from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.middleware.auth_middleware import COOKIE_NAME, get_current_user
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    UserResponse,
)
from app.services import auth_service
from app.utils.rate_limit import limiter

router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()

COOKIE_MAX_AGE: int = settings.session_expire_hours * 3600  # seconds
COOKIE_HTTPONLY: bool = True
COOKIE_SAMESITE: str = "lax"
COOKIE_PATH: str = "/"


# ── Cookie helpers ────────────────────────────────────────────────────────────

def _session_cookie_attributes() -> dict[str, object]:
    """
    Shared security attributes for session cookie creation and deletion.

    Using one source ensures set_cookie and delete_cookie always emit identical
    Secure, HttpOnly, SameSite, and Path attributes.
    """
    active_settings = get_settings()
    return {
        "httponly": COOKIE_HTTPONLY,                    # JS cannot read this cookie
        "secure": active_settings.cookie_secure,        # True in prod or when COOKIE_SECURE=true
        "samesite": active_settings.cookie_samesite,    # "lax", "strict", or "none" (for cross-origin)
        "path": COOKIE_PATH,
    }


def _set_session_cookie(response: Response, token: str) -> None:
    """Attach the session token as an HTTP-only cookie to the response."""
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=COOKIE_MAX_AGE,
        **_session_cookie_attributes(),
    )


def _clear_session_cookie(response: Response) -> None:
    """Remove the session cookie (used on logout), matching original security flags."""
    response.delete_cookie(
        key=COOKIE_NAME,
        **_session_cookie_attributes(),
    )


# ── POST /auth/register ───────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
@limiter.limit("5/minute")
async def register(
    request: Request,
    body: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """
    Create a new user, open a session, and set an HTTP-only cookie.
    The session token is NEVER returned in the response body.
    """
    try:
        user = await auth_service.register_user(
            db=db,
            email=body.email,
            full_name=body.full_name,
            plain_password=body.password,
        )
        # Login immediately after registration
        _user, token = await auth_service.login_user(
            db=db,
            email=body.email,
            plain_password=body.password,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    _set_session_cookie(response, token)
    return AuthResponse(
        message="Account created successfully.",
        user=UserResponse.model_validate(user),
    )


# ── POST /auth/login ──────────────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Log in with email and password",
)
@limiter.limit("5/minute")
async def login(
    request: Request,
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """
    Validate credentials, create a DB-backed session, set the HTTP-only cookie.
    Returns HTTP 401 on invalid credentials (message is intentionally vague).
    """
    try:
        user, token = await auth_service.login_user(
            db=db,
            email=body.email,
            plain_password=body.password,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )

    _set_session_cookie(response, token)
    return AuthResponse(
        message="Logged in successfully.",
        user=UserResponse.model_validate(user),
    )


# ── POST /auth/logout ─────────────────────────────────────────────────────────

@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Log out and invalidate the current session",
)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    session_token: Optional[str] = Cookie(default=None, alias=COOKIE_NAME),
    _current_user: User = Depends(get_current_user),  # enforces authentication
) -> MessageResponse:
    """
    Delete the session row from the DB and clear the cookie.
    Requires an active session — returns HTTP 401 if not logged in.
    Supports both cookie-based sessions and explicit Bearer tokens.
    """
    effective_token = session_token or getattr(request.state, "session_token", None)
    if effective_token:
        await auth_service.logout_user(db=db, token=effective_token)
    _clear_session_cookie(response)
    return MessageResponse(message="Logged out successfully.")


# ── GET /auth/me ──────────────────────────────────────────────────────────────

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Return the currently authenticated user",
)
async def me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Returns the authenticated user's public profile. HTTP 401 if not logged in."""
    return UserResponse.model_validate(current_user)
