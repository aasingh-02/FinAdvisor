"""
app/services/auth_service.py
─────────────────────────────
Authentication business logic — completely independent of HTTP concerns.

All DB interactions go through the injected AsyncSession.
Passwords are NEVER stored in plain text.
Session tokens are NEVER placed in response bodies (only cookies, via router).
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.session import Session
from app.models.user import User
from app.utils.security import (
    generate_session_token,
    hash_password,
    hash_session_token,
    verify_password,
)

settings = get_settings()


# ── Registration ──────────────────────────────────────────────────────────────

async def register_user(
    db: AsyncSession,
    email: str,
    full_name: str,
    plain_password: str,
) -> User:
    """
    Create a new user account.

    Raises:
        ValueError: if the email is already registered.
    """
    # Check for duplicate email (case-insensitive)
    existing = await db.execute(
        select(User).where(User.email == email.lower().strip())
    )
    if existing.scalar_one_or_none() is not None:
        raise ValueError("An account with this email already exists.")

    user = User(
        email=email.lower().strip(),
        full_name=full_name.strip(),
        hashed_password=hash_password(plain_password),  # bcrypt — never plain text
    )
    db.add(user)
    await db.flush()  # populate user.id before creating session
    return user


# ── Login ─────────────────────────────────────────────────────────────────────

async def login_user(
    db: AsyncSession,
    email: str,
    plain_password: str,
) -> tuple[User, str]:
    """
    Validate credentials and create a new DB-backed session.

    Returns:
        (user, session_token) on success.

    Raises:
        ValueError: if credentials are invalid or account is inactive.
    """
    result = await db.execute(
        select(User).where(User.email == email.lower().strip())
    )
    user: Optional[User] = result.scalar_one_or_none()

    # Deliberate constant-time path: always call verify_password
    # even when user is not found, to prevent user-enumeration via timing.
    dummy_hash = "$2b$12$eXhs79St44JlKmaR0zjB4ui6S7Qa8/x.id79XOma8D7lMqaxzBBnO"
    password_ok = verify_password(
        plain_password,
        user.hashed_password if user else dummy_hash,
    )

    if user is None or not password_ok:
        raise ValueError("Invalid email or password.")

    if not user.is_active:
        raise ValueError("This account has been deactivated. Please contact support.")

    token = await _create_session(db, user)
    return user, token


# ── Logout ────────────────────────────────────────────────────────────────────

async def logout_user(db: AsyncSession, token: str) -> None:
    """Delete the session row by its SHA-256 token hash, invalidating the session immediately."""
    if not token:
        return
    token_hash = hash_session_token(token)
    await db.execute(delete(Session).where(Session.token_hash == token_hash))


# ── Session Pruning (SEC-VULN-010) ────────────────────────────────────────────

async def prune_expired_sessions(
    db: AsyncSession,
    now: Optional[datetime] = None,
) -> int:
    """
    Delete expired session records from the database (SEC-VULN-010).

    A session is considered expired if its `expires_at` timestamp is strictly
    less than or equal to `now` (default: current UTC time).
    Active sessions (`expires_at > now`) are strictly preserved.

    Returns:
        int: Number of deleted expired session rows.
    """
    from app.services.session_cleanup import prune_expired_sessions as _prune
    return await _prune(db=db, now=now)


# ── Session validation ────────────────────────────────────────────────────────

async def get_user_from_token(
    db: AsyncSession,
    token: str,
) -> Optional[User]:
    """
    Look up the user linked to a raw session token.

    The raw token from the cookie is hashed with SHA-256 before querying the database.
    Returns None if the session doesn't exist, is expired, or the user is inactive.
    """
    if not token:
        return None

    token_hash = hash_session_token(token)
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Session)
        .where(Session.token_hash == token_hash)
        .where(Session.expires_at > now)
    )
    session: Optional[Session] = result.scalar_one_or_none()
    if session is None:
        return None

    user_result = await db.execute(
        select(User).where(User.id == session.user_id).where(User.is_active.is_(True))
    )
    return user_result.scalar_one_or_none()


# ── Internal helpers ──────────────────────────────────────────────────────────

async def _create_session(db: AsyncSession, user: User) -> str:
    """
    Generate a cryptographically secure raw token, store only its SHA-256 hash in DB,
    and return the raw token to be set exclusively in the HTTP-only cookie.
    """
    raw_token = generate_session_token()
    token_hash = hash_session_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(
        hours=settings.session_expire_hours
    )
    session = Session(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(session)
    await db.flush()
    return raw_token
