"""
app/models/session.py
─────────────────────
SQLAlchemy ORM model for the SESSIONS table.

Sessions are stored in the database so they can be explicitly revoked on
logout. The session token value is stored in an HTTP-only cookie — never
in localStorage or a response body.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Session(Base):
    __tablename__ = "sessions"

    # ── Primary key ───────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ── Foreign key ───────────────────────────────────────────────────────────
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Token Hash (SEC-VULN-002) ─────────────────────────────────────────────
    # SHA-256 hexadecimal digest (64 chars) of the cryptographically random token.
    # Raw plaintext tokens are NEVER stored in the database.
    token_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )

    # ── Expiry ────────────────────────────────────────────────────────────────
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship(  # noqa: F821
        "User",
        back_populates="sessions",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Session id={self.id} user_id={self.user_id} expires={self.expires_at}>"
