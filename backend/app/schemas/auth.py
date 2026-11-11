"""
app/schemas/auth.py
───────────────────
Pydantic request and response schemas for authentication endpoints.
These are the shapes of data that cross the HTTP boundary — ORM models
are never exposed directly.
"""

import re
import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.utils.security import MAX_PASSWORD_BYTES


def _validate_email_format(value: str) -> str:
    """Lightweight RFC-5322-compatible email check (no external dependency)."""
    pattern = r"^[a-zA-Z0-9_.+\-]+@[a-zA-Z0-9\-]+\.[a-zA-Z0-9\-.]+$"
    if not re.match(pattern, value):
        raise ValueError(f"'{value}' is not a valid email address")
    return value.lower().strip()


# ── Request schemas ───────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    """Body for POST /auth/register."""

    full_name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        examples=["Jane Doe"],
    )
    email: str = Field(..., examples=["jane@example.com"])
    password: str = Field(
        ...,
        min_length=8,
        max_length=MAX_PASSWORD_BYTES,
        examples=["Str0ng!Pass"],
    )

    @field_validator("email", mode="before")
    @classmethod
    def validate_email(cls, v: str) -> str:
        return _validate_email_format(v)

    @field_validator("full_name")
    @classmethod
    def name_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("full_name must not be blank or whitespace only")
        return v.strip()

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        """
        Enforce password security policy:
        - At most 72 UTF-8 bytes (bcrypt maximum input limit to prevent truncation)
        - At least one uppercase letter
        - At least one digit
        """
        if len(v.encode("utf-8")) > MAX_PASSWORD_BYTES:
            raise ValueError(f"Password must not exceed {MAX_PASSWORD_BYTES} UTF-8 bytes")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class LoginRequest(BaseModel):
    """Body for POST /auth/login."""

    email: str = Field(..., examples=["jane@example.com"])
    password: str = Field(..., min_length=1, max_length=MAX_PASSWORD_BYTES)

    @field_validator("email", mode="before")
    @classmethod
    def validate_email(cls, v: str) -> str:
        return _validate_email_format(v)

    @field_validator("password")
    @classmethod
    def validate_password_byte_length(cls, v: str) -> str:
        """
        Consistent validation during login: reject oversized passwords safely
        without silently accepting a truncated equivalent.
        """
        if len(v.encode("utf-8")) > MAX_PASSWORD_BYTES:
            raise ValueError(f"Password must not exceed {MAX_PASSWORD_BYTES} UTF-8 bytes")
        return v


# ── Response schemas ──────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    """Public user representation — no password or token fields."""

    id: uuid.UUID
    email: str
    full_name: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    """Returned on successful register / login."""

    message: str
    user: UserResponse


class MessageResponse(BaseModel):
    """Generic single-message response (e.g. logout)."""

    message: str
