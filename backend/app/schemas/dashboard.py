"""
app/schemas/dashboard.py
────────────────────────
Pydantic schemas for the Unified Financial Dashboard & Financial Health Score Engine.
All monetary amounts, rates, weights, and scores use Python Decimal for precision.
"""

from decimal import Decimal
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class HealthGradeEnum(str, Enum):
    A_PLUS = "A+"
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"


class HealthSubScoreItem(BaseModel):
    name: str = Field(..., description="Name of the sub-score component")
    score: Decimal = Field(..., description="Raw sub-score out of 100")
    weight_percentage: Decimal = Field(..., description="Weight assigned in composite formula (e.g. 35%)")
    weighted_score: Decimal = Field(..., description="Weighted contribution to final score")
    status: str = Field(..., description="Qualitative rating: Optimal, Good, Moderate, Stretched, Critical")
    detail: str = Field(..., description="Contextual explanation of this metric")

    model_config = {"from_attributes": True}


class FinancialHealthScore(BaseModel):
    overall_score: Decimal = Field(..., description="Composite health score from 0.00 to 100.00")
    letter_grade: HealthGradeEnum = Field(..., description="Letter grade rating (A+, A, B, C, D, F)")
    status_label: str = Field(..., description="Human-readable rating label")
    summary: str = Field(..., description="Concise assessment of the user's financial resilience")
    sub_scores: List[HealthSubScoreItem] = Field(..., description="Detailed 4-factor scoring breakdown")

    model_config = {"from_attributes": True}


class DashboardMetricCards(BaseModel):
    monthly_net_income: Decimal = Field(..., description="Net monthly earnings in INR")
    total_active_loans: int = Field(..., description="Active loan count")
    monthly_emi_burden: Decimal = Field(..., description="Total monthly EMI commitments in INR")
    monthly_living_expenses: Decimal = Field(..., description="Essential living costs in INR")
    disposable_monthly_cash_flow: Decimal = Field(..., description="Uncommitted monthly surplus cash in INR")
    emergency_fund_months: Decimal = Field(..., description="Reserve liquidity expressed in months of living costs")
    emergency_savings_total: Decimal = Field(..., description="Total emergency savings in INR")
    prudent_max_monthly_emi: Decimal = Field(..., description="Maximum prudent EMI capacity after safety buffers")

    model_config = {"from_attributes": True}


class DashboardSummaryResponse(BaseModel):
    profile_complete: bool = Field(..., description="Whether the user has initialized their financial profile")
    health_score: Optional[FinancialHealthScore] = Field(default=None, description="Calculated financial health score")
    metrics: Optional[DashboardMetricCards] = Field(default=None, description="Core dashboard metric cards")
    current_foir_percentage: Optional[Decimal] = Field(default=None, description="Current FOIR debt ratio percentage")
    foir_status: Optional[str] = Field(default=None, description="FOIR tier: Optimal, Manageable, Stretched, Risky")
    overall_risk_category: Optional[str] = Field(default=None, description="Risk tier: LOW, MODERATE, HIGH, CRITICAL")
    overall_risk_score: Optional[Decimal] = Field(default=None, description="Risk diagnostic score (0 to 100)")
    is_borrowing_eligible: Optional[bool] = Field(default=None, description="Whether additional borrowing is advisable")
    prudent_max_borrowing_emi: Optional[Decimal] = Field(default=None, description="Prudent safe monthly borrowing headroom")
    top_recommendation_summary: Optional[str] = Field(default=None, description="Summary of loan borrowing capacity")
    active_warnings: List[str] = Field(default_factory=list, description="Prioritized cautionary alerts or notes")
    actionable_highlights: List[str] = Field(default_factory=list, description="Key suggested next financial steps")

    model_config = {"from_attributes": True}
