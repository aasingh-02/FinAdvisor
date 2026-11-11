"""
app/routers/emi.py
──────────────────
HTTP router for EMI calculation and amortization schedule operations.

Endpoints:
- POST /api/v1/emi/calculate -> Compute standard reducing-balance EMI and schedule
"""

from fastapi import APIRouter, Depends, status

from app.middleware.auth_middleware import get_current_user
from app.models.user import User
from app.schemas.emi import EMICalculationRequest, EMICalculationResponse
from app.services import emi_service

router = APIRouter(prefix="/emi", tags=["EMI Calculator"])


@router.post(
    "/calculate",
    response_model=EMICalculationResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate reducing-balance EMI and amortization schedule",
)
async def calculate_emi(
    body: EMICalculationRequest,
    current_user: User = Depends(get_current_user),
) -> EMICalculationResponse:
    """
    Deterministic EMI calculator.

    Accepts:
    - principal_amount: Loan amount (> 0)
    - annual_interest_rate: Annual percentage interest rate (>= 0)
    - tenure_months: Total repayment period in months (> 0)

    Returns:
    - monthly_emi: Standard monthly installment
    - total_interest: Total interest payable over tenure
    - total_repayment: Sum of all installments (Principal + Total Interest)
    - principal_percentage & interest_percentage: Visual breakdown proportions
    - amortization_schedule: Month-by-month repayment schedule
    """
    return emi_service.calculate_emi_with_schedule(
        principal_amount=body.principal_amount,
        annual_interest_rate=body.annual_interest_rate,
        tenure_months=body.tenure_months,
    )
