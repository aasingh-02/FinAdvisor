"""
app/models/financial_profile.py
───────────────────────────────
SQLAlchemy ORM model for the FINANCIAL_PROFILES table.

Stores the user's financial profile: income, regular expenses,
existing loan EMI obligations, and emergency savings.
Every record is strictly associated with a User (1-to-1).
Financial figures use Numeric(12, 2) mapped to Python Decimal.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class FinancialProfile(Base):
    __tablename__ = "financial_profiles"

    # ── Primary key ───────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ── Foreign key (1-to-1 with users) ───────────────────────────────────────
    # unique=True enforces single profile per user and automatically creates a unique index.
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # ── Financial Amounts (Decimal/Numeric for currency precision) ───────────
    monthly_net_income: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )
    monthly_expenses: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    existing_monthly_emi: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    emergency_savings: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    # ── Employment & Loan metadata ────────────────────────────────────────────
    employment_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="SALARIED",
    )
    existing_loan_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # ── Relationship ──────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship(  # noqa: F821
        "User",
        back_populates="financial_profile",
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<FinancialProfile id={self.id} user_id={self.user_id} "
            f"income={self.monthly_net_income} emi={self.existing_monthly_emi}>"
        )
