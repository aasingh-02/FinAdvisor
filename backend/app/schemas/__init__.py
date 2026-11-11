"""
app/schemas/__init__.py
"""

from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    UserResponse,
    AuthResponse,
    MessageResponse,
)
from app.schemas.financial_profile import (
    FinancialProfileCreate,
    FinancialProfileUpdate,
    FinancialProfileResponse,
    ProfileMessageResponse,
    EmploymentTypeEnum,
)
from app.schemas.emi import (
    EMICalculationRequest,
    AmortizationScheduleItem,
    EMICalculationResponse,
)

__all__ = [
    "RegisterRequest",
    "LoginRequest",
    "UserResponse",
    "AuthResponse",
    "MessageResponse",
    "FinancialProfileCreate",
    "FinancialProfileUpdate",
    "FinancialProfileResponse",
    "ProfileMessageResponse",
    "EmploymentTypeEnum",
    "EMICalculationRequest",
    "AmortizationScheduleItem",
    "EMICalculationResponse",
]
