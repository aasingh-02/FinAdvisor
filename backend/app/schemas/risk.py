"""
app/schemas/risk.py
───────────────────
Pydantic schemas for Financial Risk Assessment and Advisory Engine.
Uses Python Decimal for financial amounts, ratios, and risk scores.
"""

from decimal import Decimal
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class RiskLevelEnum(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RecommendationPriorityEnum(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskIndicatorDetail(BaseModel):
    indicator_key: str = Field(..., description="Unique key for indicator (e.g. FOIR, EMERGENCY_FUND)")
    indicator_name: str = Field(..., description="Human-readable title for the indicator")
    score: Decimal = Field(..., description="Risk score for this indicator (0.00 to 100.00)")
    risk_level: RiskLevelEnum = Field(..., description="Classification level: LOW, MODERATE, HIGH, CRITICAL")
    value_display: str = Field(..., description="Formatted value (e.g. '25.00%', '4.50 months', '₹40,000.00')")
    explanation: str = Field(..., description="Detailed description of the indicator assessment")

    model_config = {"from_attributes": True}


class AdvisoryRecommendation(BaseModel):
    title: str = Field(..., description="Short title of the recommendation")
    explanation: str = Field(..., description="Contextual reason for this recommendation")
    priority: RecommendationPriorityEnum = Field(..., description="Urgency priority: LOW, MEDIUM, HIGH, CRITICAL")
    related_indicator: str = Field(..., description="Which risk indicator triggered this recommendation")
    suggested_action: str = Field(..., description="Concrete, actionable step the user should take")

    model_config = {"from_attributes": True}


class RiskAssessmentResponse(BaseModel):
    # Core Overall Risk Metrics
    overall_risk_score: Decimal = Field(
        ...,
        description="Overall weighted financial risk score (0.00 to 100.00)",
        examples=[Decimal("22.50")],
    )
    overall_risk_category: RiskLevelEnum = Field(
        ...,
        description="Overall risk category: LOW, MODERATE, HIGH, or CRITICAL",
        examples=[RiskLevelEnum.LOW],
    )

    # Underlying Financial Figures
    monthly_net_income: Decimal = Field(..., description="Monthly net in-hand income")
    existing_monthly_emi: Decimal = Field(..., description="Total existing monthly loan obligations")
    monthly_expenses: Decimal = Field(..., description="Monthly household living expenses")
    emergency_savings: Decimal = Field(..., description="Liquid emergency reserve")
    disposable_monthly_income: Decimal = Field(..., description="Remaining income after EMIs and living expenses")

    # Ratio Metrics
    foir_percentage: Decimal = Field(..., description="Current FOIR percentage")
    current_foir_percentage: Decimal = Field(..., description="Alias for current FOIR percentage")
    configured_foir_threshold: Decimal = Field(..., description="Configured policy threshold percentage")
    emergency_fund_coverage_months: Decimal = Field(..., description="Coverage in months (savings / expenses)")

    # Diagnostic Breakdowns & Actions
    indicators: List[RiskIndicatorDetail] = Field(..., description="Individual risk indicator assessments")
    triggered_warnings: List[str] = Field(default_factory=list, description="Active warning flags triggered by high-risk conditions")
    recommendations: List[AdvisoryRecommendation] = Field(default_factory=list, description="Tailored actionable financial advice")
    summary_message: str = Field(..., description="Comprehensive explanatory executive summary")
    assessment_disclaimer: str = Field(
        default=(
            "This assessment is an illustrative personal financial health analysis based on self-reported profile data. "
            "It is not a credit bureau score (e.g. CIBIL/Experian), formal lender underwriting evaluation, or loan approval guarantee."
        ),
        description="Legal and illustrative compliance disclaimer",
    )

    model_config = {"from_attributes": True}
