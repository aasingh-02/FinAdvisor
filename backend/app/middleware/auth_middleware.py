"""
app/middleware/auth_middleware.py
─────────────────────────────────
FastAPI dependency that validates the HTTP-only session cookie or explicit
Authorization: Bearer header for non-browser API clients, and returns the
authenticated User, or raises HTTP 401.

Usage in a router:
    @router.get("/protected")
    async def protected_route(current_user: User = Depends(get_current_user)):
        ...
"""

from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.services.auth_service import get_user_from_token

COOKIE_NAME = "session_token"


async def get_current_user(
    request: Request,
    session_token: Optional[str] = Cookie(default=None, alias=COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    FastAPI dependency — extracts the session_token from either:
    1. The HTTP-only session cookie (standard browser clients)
    2. The explicit 'Authorization: Bearer <token>' header (non-browser API clients)

    Validates it against the database and returns the active User.

    Raises HTTP 401 if:
    - Neither cookie nor Bearer token is provided
    - Token is not found in DB
    - Token is expired
    - Associated user is inactive
    """
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated. Please log in.",
        headers={"WWW-Authenticate": "Cookie, Bearer"},
    )

    # 1. Primary browser authentication: HTTP-only session cookie
    token = session_token

    # 2. Explicit non-browser authentication: Authorization header
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()

    if not token:
        raise credentials_error

    user = await get_user_from_token(db, token)
    if user is None:
        raise credentials_error

    request.state.user = user
    request.state.user_id = str(user.id)
    request.state.session_token = token
    return user
