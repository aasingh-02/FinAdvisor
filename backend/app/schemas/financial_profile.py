"""
app/schemas/financial_profile.py
─────────────────────────────────
Pydantic schemas for User Financial Profile requests and responses.
All monetary amounts are represented as Decimal with 2 decimal places.
Input validation guards strictly enforce non-negative values and positive income.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class EmploymentTypeEnum(str, Enum):
    SALARIED = "SALARIED"
    SELF_EMPLOYED = "SELF_EMPLOYED"
    BUSINESS = "BUSINESS"
    OTHER = "OTHER"


# Maximum monetary value supported by PostgreSQL Numeric(12, 2) column precision.
# Numeric(12, 2) supports up to 10 integer digits and 2 fractional digits: 9,999,999,999.99
MAX_FINANCIAL_AMOUNT = Decimal("9999999999.99")
MAX_MONETARY_DIGITS = 12
MONETARY_DECIMAL_PLACES = 2
MAX_LOAN_COUNT = 1000


# ── Base schema ───────────────────────────────────────────────────────────────

class FinancialProfileBase(BaseModel):
    monthly_net_income: Decimal = Field(
        ...,
        gt=0,
        le=MAX_FINANCIAL_AMOUNT,
        max_digits=MAX_MONETARY_DIGITS,
        decimal_places=MONETARY_DECIMAL_PLACES,
        description="Net monthly in-hand income (must be greater than 0, up to 9,999,999,999.99)",
        examples=[Decimal("75000.00")],
    )
    monthly_expenses: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        le=MAX_FINANCIAL_AMOUNT,
        max_digits=MAX_MONETARY_DIGITS,
        decimal_places=MONETARY_DECIMAL_PLACES,
        description="Regular monthly living and household expenses",
        examples=[Decimal("30000.00")],
    )
    existing_monthly_emi: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        le=MAX_FINANCIAL_AMOUNT,
        max_digits=MAX_MONETARY_DIGITS,
        decimal_places=MONETARY_DECIMAL_PLACES,
        description="Total existing monthly loan and credit EMI obligations",
        examples=[Decimal("15000.00")],
    )
    emergency_savings: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        le=MAX_FINANCIAL_AMOUNT,
        max_digits=MAX_MONETARY_DIGITS,
        decimal_places=MONETARY_DECIMAL_PLACES,
        description="Total liquid savings available for emergencies",
        examples=[Decimal("200000.00")],
    )
    employment_type: EmploymentTypeEnum = Field(
        default=EmploymentTypeEnum.SALARIED,
        description="Employment categorization",
    )
    existing_loan_count: int = Field(
        default=0,
        ge=0,
        le=MAX_LOAN_COUNT,
        description="Number of currently active loan obligations",
        examples=[1],
    )

    @field_validator(
        "monthly_net_income",
        "monthly_expenses",
        "existing_monthly_emi",
        "emergency_savings",
        mode="after",
    )
    @classmethod
    def round_to_two_decimals(cls, v: Decimal) -> Decimal:
        return round(v, 2)


# ── Create / Replace (PUT) ────────────────────────────────────────────────────

class FinancialProfileCreate(FinancialProfileBase):
    """Payload for creating or fully replacing the profile."""
    pass


# ── Partial Update (PATCH) ────────────────────────────────────────────────────

class FinancialProfileUpdate(BaseModel):
    """
    Payload for partial profile updates.
    All fields are optional, but any provided field cannot be null and must pass range checks.
    """
    monthly_net_income: Optional[Decimal] = Field(
        None,
        gt=0,
        le=MAX_FINANCIAL_AMOUNT,
        max_digits=MAX_MONETARY_DIGITS,
        decimal_places=MONETARY_DECIMAL_PLACES,
    )
    monthly_expenses: Optional[Decimal] = Field(
        None,
        ge=0,
        le=MAX_FINANCIAL_AMOUNT,
        max_digits=MAX_MONETARY_DIGITS,
        decimal_places=MONETARY_DECIMAL_PLACES,
    )
    existing_monthly_emi: Optional[Decimal] = Field(
        None,
        ge=0,
        le=MAX_FINANCIAL_AMOUNT,
        max_digits=MAX_MONETARY_DIGITS,
        decimal_places=MONETARY_DECIMAL_PLACES,
    )
    emergency_savings: Optional[Decimal] = Field(
        None,
        ge=0,
        le=MAX_FINANCIAL_AMOUNT,
        max_digits=MAX_MONETARY_DIGITS,
        decimal_places=MONETARY_DECIMAL_PLACES,
    )
    employment_type: Optional[EmploymentTypeEnum] = None
    existing_loan_count: Optional[int] = Field(None, ge=0, le=MAX_LOAN_COUNT)

    @field_validator(
        "monthly_net_income",
        "monthly_expenses",
        "existing_monthly_emi",
        "emergency_savings",
        mode="after",
    )
    @classmethod
    def round_to_two_decimals(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None:
            return round(v, 2)
        return v


# ── Response schema ───────────────────────────────────────────────────────────

class FinancialProfileResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    monthly_net_income: Decimal
    monthly_expenses: Decimal
    existing_monthly_emi: Decimal
    emergency_savings: Decimal
    employment_type: str
    existing_loan_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProfileMessageResponse(BaseModel):
    message: str
    profile: FinancialProfileResponse
