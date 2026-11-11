"""
app/utils/security.py
─────────────────────
Security utilities:
  - bcrypt password hashing / verification (with 72-byte truncation defense)
  - Cryptographically secure session token generation
"""

import hashlib
import secrets

import bcrypt

MAX_PASSWORD_BYTES = 72


# ── Password helpers ──────────────────────────────────────────────────────────

def hash_password(plain_password: str) -> str:
    """
    Hash a plain-text password with bcrypt (cost factor 12).

    Returns the hash as a UTF-8 string ready for DB storage.
    NEVER store the plain-text password.

    Enforces maximum length of 72 UTF-8 bytes to prevent bcrypt's
    silent truncation vulnerability (SEC-VULN-007).
    """
    password_bytes = plain_password.encode("utf-8")
    if len(password_bytes) > MAX_PASSWORD_BYTES:
        raise ValueError(
            f"Password must not exceed {MAX_PASSWORD_BYTES} UTF-8 bytes."
        )
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain-text password against a stored bcrypt hash.

    Uses a constant-time comparison internally — safe against timing attacks.
    Rejects passwords exceeding 72 UTF-8 bytes immediately to prevent
    bcrypt from silently truncating and matching passwords with arbitrary suffixes.
    """
    if not plain_password or not hashed_password:
        return False

    password_bytes = plain_password.encode("utf-8")
    if len(password_bytes) > MAX_PASSWORD_BYTES:
        return False

    try:
        return bcrypt.checkpw(
            password_bytes,
            hashed_password.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False


# ── Session token helpers ─────────────────────────────────────────────────────

def generate_session_token(nbytes: int = 64) -> str:
    """
    Generate a cryptographically secure URL-safe session token.

    Default: 64 bytes → 86 characters of base64url — effectively unguessable.
    """
    return secrets.token_urlsafe(nbytes)


def hash_session_token(token: str) -> str:
    """
    Compute the SHA-256 hexadecimal digest of a raw session token.

    Only this 64-character hash is persisted in the database or used for session queries.
    Raw session tokens are NEVER stored in the database.
    """
    if not token:
        return ""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
