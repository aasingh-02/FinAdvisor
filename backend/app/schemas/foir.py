"""
app/schemas/foir.py
───────────────────
Pydantic schemas for FOIR (Fixed Obligation to Income Ratio) calculation
and financial affordability assessment.

All monetary figures and percentages use Python Decimal for precision.
"""

from decimal import Decimal
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class AffordabilityStatusEnum(str, Enum):
    OPTIMAL = "Optimal"
    MANAGEABLE = "Manageable"
    STRETCHED = "Stretched"
    CRITICAL = "Critical"


class FOIRCalculationResponse(BaseModel):
    # User Financial Profile inputs
    monthly_net_income: Decimal = Field(
        ...,
        description="Net monthly in-hand income",
        examples=[Decimal("85000.00")],
    )
    existing_monthly_emi: Decimal = Field(
        ...,
        description="Total existing monthly loan and credit EMI obligations",
        examples=[Decimal("20000.00")],
    )
    monthly_expenses: Decimal = Field(
        ...,
        description="Regular monthly living and household expenses",
        examples=[Decimal("35000.00")],
    )
    emergency_savings: Decimal = Field(
        ...,
        description="Liquid emergency savings reserve",
        examples=[Decimal("250000.00")],
    )

    # Core FOIR & Capacity Calculations
    current_foir_percentage: Decimal = Field(
        ...,
        description="Current FOIR percentage: (existing_monthly_emi / monthly_net_income) * 100",
        examples=[Decimal("23.53")],
    )
    configured_foir_threshold: Decimal = Field(
        ...,
        description="Configured FOIR policy benchmark percentage (default: 40.00%)",
        examples=[Decimal("40.00")],
    )
    maximum_permissible_emi: Decimal = Field(
        ...,
        description="Maximum permissible total monthly EMI under configured threshold",
        examples=[Decimal("34000.00")],
    )
    additional_emi_capacity: Decimal = Field(
        ...,
        description="Available additional monthly EMI headroom (max(0, maximum_permissible_emi - existing_monthly_emi))",
        examples=[Decimal("14000.00")],
    )
    remaining_income_after_expenses_and_emi: Decimal = Field(
        ...,
        description="Net monthly disposable cash flow after paying living expenses and existing EMIs",
        examples=[Decimal("30000.00")],
    )

    # Classification & Narrative
    affordability_status: AffordabilityStatusEnum = Field(
        ...,
        description="Affordability risk tier (Optimal, Manageable, Stretched, Critical)",
        examples=[AffordabilityStatusEnum.OPTIMAL],
    )
    explanatory_message: str = Field(
        ...,
        description="Clear contextual summary of user affordability and borrowing headroom",
    )

    # Optional Proposed Loan Simulation Fields
    proposed_emi: Optional[Decimal] = Field(
        None,
        description="Optional proposed EMI amount evaluated in this calculation",
        examples=[Decimal("5000.00")],
    )
    projected_foir_percentage: Optional[Decimal] = Field(
        None,
        description="Projected FOIR percentage if the proposed EMI is undertaken",
        examples=[Decimal("29.41")],
    )

    model_config = {"from_attributes": True}
