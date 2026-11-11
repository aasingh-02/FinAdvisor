"""
app/schemas/recommendation.py
──────────────────────────────
Pydantic schemas for the Personalized Loan Recommendation Engine.
All monetary amounts, rates, and ratios use Python Decimal for precision.
"""

from decimal import Decimal
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class LoanCategoryEnum(str, Enum):
    PERSONAL_LOAN = "PERSONAL_LOAN"
    HOME_LOAN = "HOME_LOAN"
    VEHICLE_LOAN = "VEHICLE_LOAN"
    EDUCATION_LOAN = "EDUCATION_LOAN"


class RecommendationRequest(BaseModel):
    foir_threshold: Optional[Decimal] = Field(
        default=Decimal("40.00"),
        ge=Decimal("1.00"),
        le=Decimal("100.00"),
        description="Configurable FOIR policy threshold percentage (1.00% to 100.00%)",
        examples=[Decimal("40.00")],
    )
    preferred_loan_category: Optional[LoanCategoryEnum] = Field(
        default=None,
        description="Optional preferred loan category (PERSONAL_LOAN, HOME_LOAN, VEHICLE_LOAN, EDUCATION_LOAN)",
    )
    desired_loan_amount: Optional[Decimal] = Field(
        default=None,
        gt=Decimal("0.00"),
        le=Decimal("100000000.00"),
        description="Optional requested loan amount to evaluate affordability against",
        examples=[Decimal("500000.00")],
    )
    preferred_tenure_months: Optional[int] = Field(
        default=None,
        ge=6,
        le=360,
        description="Optional preferred tenure in months (6 to 360 months)",
        examples=[60],
    )


class LoanRecommendationItem(BaseModel):
    loan_category: LoanCategoryEnum = Field(..., description="Loan category identifier")
    category_display_name: str = Field(..., description="Human-readable category title")
    recommended_principal: Decimal = Field(..., description="Prudent suggested principal amount in INR")
    assumed_annual_interest_rate: Decimal = Field(..., description="Assumed illustrative interest rate percentage")
    suggested_tenure_months: int = Field(..., description="Suggested loan repayment duration in months")
    estimated_monthly_emi: Decimal = Field(..., description="Estimated monthly EMI calculated by reducing-balance engine")
    total_interest_payable: Decimal = Field(..., description="Total interest paid over the entire tenure")
    total_repayment: Decimal = Field(..., description="Total loan repayment (Principal + Interest)")
    projected_foir_percentage: Decimal = Field(..., description="Projected FOIR percentage including this proposed loan")
    affordability_classification: str = Field(..., description="Affordability tier: Optimal, Manageable, or Stretched")
    suitability_reason: str = Field(..., description="Contextual explanation of why this scenario fits user cash flow")

    model_config = {"from_attributes": True}


class FinancialEligibilitySnapshot(BaseModel):
    monthly_net_income: Decimal = Field(..., description="Monthly take-home earnings")
    existing_monthly_emi: Decimal = Field(..., description="Existing monthly loan obligations")
    monthly_expenses: Decimal = Field(..., description="Monthly household living costs")
    emergency_savings: Decimal = Field(..., description="Total liquid emergency reserve")
    current_foir_percentage: Decimal = Field(..., description="Current debt ratio percentage")
    configured_foir_threshold: Decimal = Field(..., description="Configured policy benchmark threshold")
    disposable_monthly_income: Decimal = Field(..., description="Remaining monthly cash flow after expenses and EMIs")
    theoretical_additional_capacity: Decimal = Field(..., description="Raw mathematical capacity under FOIR policy")
    prudent_max_monthly_emi: Decimal = Field(..., description="Prudent maximum EMI after applying cash-flow safety margins")
    employment_type: str = Field(..., description="Employment categorization (Salaried, Self-Employed, etc.)")

    model_config = {"from_attributes": True}


class RiskConsiderations(BaseModel):
    overall_risk_category: str = Field(..., description="Risk category: LOW, MODERATE, HIGH, CRITICAL")
    overall_risk_score: Decimal = Field(..., description="Composite risk score (0 to 100)")
    emergency_fund_coverage_months: Decimal = Field(..., description="Emergency fund coverage in months of living expenses")
    has_sufficient_emergency_fund: bool = Field(..., description="Whether emergency reserve covers at least 3 months")
    has_cash_deficit: bool = Field(..., description="Whether living costs and EMIs exceed income")

    model_config = {"from_attributes": True}


class RecommendationResponse(BaseModel):
    is_eligible: bool = Field(..., description="Whether the user currently qualifies for additional borrowing")
    eligibility_summary: str = Field(..., description="Executive summary of user borrowing eligibility and headroom")
    financial_snapshot: FinancialEligibilitySnapshot = Field(..., description="Current financial profile snapshot")
    risk_considerations: RiskConsiderations = Field(..., description="Key risk metrics influencing borrowing headroom")
    recommendations: List[LoanRecommendationItem] = Field(default_factory=list, description="Personalized loan recommendations")
    reasons_and_warnings: List[str] = Field(default_factory=list, description="Specific advisory warnings or cautionary notes")
    assumptions_and_disclaimers: str = Field(..., description="Mandatory underwriting disclaimers and rate assumptions")

    model_config = {"from_attributes": True}
