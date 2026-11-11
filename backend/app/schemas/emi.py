"""
app/schemas/emi.py
──────────────────
Pydantic schemas for EMI calculations and amortization schedule generation.
Uses Python Decimal for monetary precision.
"""

from decimal import Decimal
from typing import List
from pydantic import BaseModel, Field, field_validator


class EMICalculationRequest(BaseModel):
    principal_amount: Decimal = Field(
        ...,
        gt=0,
        le=Decimal("1000000000.00"),  # Sensible upper bound: 100 Crores
        description="Loan principal amount (must be > 0)",
        examples=[Decimal("1000000.00")],
    )
    annual_interest_rate: Decimal = Field(
        ...,
        ge=0,
        le=Decimal("100.00"),  # Sensible upper bound: 100% per annum
        description="Annual interest rate percentage (0% to 100%)",
        examples=[Decimal("9.00")],
    )
    tenure_months: int = Field(
        ...,
        gt=0,
        le=600,  # Sensible upper bound: 50 years (600 months)
        description="Loan repayment tenure in months (1 to 600)",
        examples=[60],
    )

    @field_validator("principal_amount", "annual_interest_rate", mode="after")
    @classmethod
    def round_inputs(cls, v: Decimal) -> Decimal:
        return round(v, 2)


class AmortizationScheduleItem(BaseModel):
    month: int = Field(..., description="Installment month number (1 to n)")
    opening_balance: Decimal = Field(..., description="Outstanding principal at beginning of month")
    emi_amount: Decimal = Field(..., description="Total monthly installment amount")
    principal_component: Decimal = Field(..., description="Principal amount repaid in this installment")
    interest_component: Decimal = Field(..., description="Interest amount paid in this installment")
    closing_balance: Decimal = Field(..., description="Remaining principal at end of month")

    model_config = {"from_attributes": True}


class EMICalculationResponse(BaseModel):
    principal_amount: Decimal = Field(..., description="Original loan principal amount")
    annual_interest_rate: Decimal = Field(..., description="Annual interest rate percentage")
    tenure_months: int = Field(..., description="Loan tenure in months")
    monthly_emi: Decimal = Field(..., description="Standard monthly EMI amount")
    total_interest: Decimal = Field(..., description="Total interest payable over loan tenure")
    total_repayment: Decimal = Field(..., description="Total amount payable (Principal + Total Interest)")
    principal_percentage: Decimal = Field(..., description="Principal as percentage of total repayment")
    interest_percentage: Decimal = Field(..., description="Interest as percentage of total repayment")
    amortization_schedule: List[AmortizationScheduleItem] = Field(
        default_factory=list,
        description="Monthly amortization breakdown",
    )

    model_config = {"from_attributes": True}
