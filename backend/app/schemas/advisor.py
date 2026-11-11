"""
app/schemas/advisor.py
──────────────────────
Pydantic schemas for the AI Financial Advisor & Copilot engine.
Enforces input validation, sanitized role/content structure, and separate verified financial figures.
"""

from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, field_validator


class AdvisorContextEnum(str, Enum):
    GENERAL = "GENERAL"
    HEALTH_SCORE = "HEALTH_SCORE"
    FOIR_AFFORDABILITY = "FOIR_AFFORDABILITY"
    RISK_ASSESSMENT = "RISK_ASSESSMENT"
    LOAN_RECOMMENDATIONS = "LOAN_RECOMMENDATIONS"
    EMI_SIMULATION = "EMI_SIMULATION"


class ChatRoleEnum(str, Enum):
    USER = "user"
    MODEL = "model"


class ChatMessage(BaseModel):
    role: ChatRoleEnum = Field(..., description="Message author role: 'user' or 'model'")
    content: str = Field(..., min_length=1, max_length=10000, description="Message text")

    @field_validator("content", mode="before")
    @classmethod
    def sanitize_and_truncate_history(cls, v: Any) -> str:
        if not isinstance(v, str):
            v = str(v) if v is not None else ""
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Message content cannot be blank or whitespace only")
        # Safely truncate oversized historical messages (such as previous long assistant answers)
        # to 1500 chars so that context remains bounded without breaking validation
        if len(cleaned) > 1500:
            return cleaned[:1485] + "... [truncated]"
        return cleaned


class AdvisorChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=2,
        max_length=1000,
        description="User financial query or advisory prompt",
        examples=["Can I comfortably afford a new personal loan of ₹3,00,000?"],
    )
    context: Optional[AdvisorContextEnum] = Field(
        default=AdvisorContextEnum.GENERAL,
        description="Focused context area for the advisory guidance",
    )
    history: Optional[List[ChatMessage]] = Field(
        default_factory=list,
        description="Recent conversation context (max 6 turns)",
    )

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        cleaned = v.strip()
        if len(cleaned) < 2:
            raise ValueError("Message must contain at least 2 characters")
        if len(cleaned) > 1000:
            raise ValueError("Message must be at most 1000 characters long")
        return cleaned

    @field_validator("history", mode="after")
    @classmethod
    def cap_history_turns(cls, v: Optional[List[ChatMessage]]) -> List[ChatMessage]:
        if not v:
            return []
        # Strictly keep only the last 6 history messages
        return v[-6:]


class AdvisorExplainRequest(BaseModel):
    context: AdvisorContextEnum = Field(
        ...,
        description="Financial component to explain (HEALTH_SCORE, FOIR_AFFORDABILITY, etc.)",
    )
    user_query: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional specific question about this financial metric",
    )
    custom_scenario: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional custom simulation payload (e.g. proposed loan amount or tenure)",
    )


class FinancialSnapshotSummary(BaseModel):
    """
    Factual verified numbers derived purely from the backend deterministic Python engine.
    Gemini is grounded on these figures and never calculates them.
    """
    monthly_net_income: Decimal = Field(..., description="Take-home monthly earnings in INR")
    monthly_living_expenses: Decimal = Field(..., description="Regular essential household costs in INR")
    existing_monthly_emi: Decimal = Field(..., description="Current total monthly loan obligations in INR")
    disposable_monthly_cash_flow: Decimal = Field(..., description="Monthly cash surplus or deficit in INR")
    emergency_savings_total: Decimal = Field(..., description="Total liquid emergency reserve in INR")
    emergency_fund_months: Decimal = Field(..., description="Emergency reserve depth in months")
    total_active_loans: int = Field(..., description="Number of active loan facilities")
    current_foir_percentage: Decimal = Field(..., description="Fixed Obligation to Income Ratio percentage")
    foir_status: str = Field(..., description="FOIR policy tier: Optimal, Manageable, Stretched, Critical, No Debt")
    overall_health_score: Optional[Decimal] = Field(default=None, description="Composite health index (0 to 100)")
    letter_grade: Optional[str] = Field(default=None, description="Letter grade rating (A+, A, B, C, D, F)")
    overall_risk_category: str = Field(..., description="Risk tier: LOW, MODERATE, HIGH, CRITICAL")
    is_borrowing_eligible: bool = Field(..., description="Whether additional borrowing is currently safe")
    prudent_max_monthly_emi: Decimal = Field(..., description="Prudent safe monthly borrowing headroom in INR")

    model_config = {"from_attributes": True}


class AdvisorResponse(BaseModel):
    reply: str = Field(..., description="AI-generated financial explanation and guidance")
    context_used: AdvisorContextEnum = Field(..., description="Financial context domain applied")
    financial_snapshot: Optional[FinancialSnapshotSummary] = Field(
        default=None,
        description="Verified deterministic figures used for grounding the advisory response",
    )
    disclaimer: str = Field(
        ...,
        description="Transparency and regulatory non-underwriting disclaimer",
    )
    is_fallback: bool = Field(
        default=False,
        description="True if generated by the deterministic fallback engine when Gemini was unavailable",
    )
    model_used: str = Field(
        ...,
        description="Name of the Gemini model or deterministic engine used",
    )

    model_config = {"from_attributes": True}
