"""
app/routers/foir.py
───────────────────
HTTP router for FOIR (Fixed Obligation to Income Ratio) calculation and
borrowing capacity advisory.

Endpoints:
- GET /api/v1/foir/calculate -> Evaluate current user's FOIR, maximum permissible EMI,
                                and available additional borrowing capacity.
"""

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.models.user import User
from app.schemas.foir import FOIRCalculationResponse
from app.services import foir_service, profile_service

router = APIRouter(prefix="/foir", tags=["FOIR Calculator"])


@router.get(
    "/calculate",
    response_model=FOIRCalculationResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate FOIR and borrowing affordability for current user",
)
async def calculate_current_user_foir(
    threshold: Decimal = Query(
        Decimal("40.00"),
        ge=Decimal("1.00"),
        le=Decimal("100.00"),
        description="Configured FOIR policy benchmark percentage (default: 40.00%)",
        examples=[Decimal("40.00")],
    ),
    proposed_emi: Optional[Decimal] = Query(
        None,
        ge=Decimal("0.00"),
        description="Optional proposed loan monthly EMI to evaluate impact on FOIR",
        examples=[Decimal("15000.00")],
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FOIRCalculationResponse:
    """
    Evaluate Fixed Obligation to Income Ratio (FOIR) using the authenticated user's profile.

    - Authenticated access required via HTTP-only session cookie.
    - Retrieves the caller's financial profile from the database.
    - Returns HTTP 404 if the user has not yet initialized a financial profile.
    - Computes:
        * current_foir_percentage
        * maximum_permissible_emi under the configured policy threshold
        * additional_emi_capacity (strictly >= 0)
        * remaining_income_after_expenses_and_emi
        * affordability_status classification (Optimal, Manageable, Stretched, Critical)
        * explanatory_message highlighting policy context vs. lender criteria
    - Calculations are pure in-memory deterministic operations; nothing is written to DB.
    """
    profile = await profile_service.get_profile_by_user_id(db, current_user.id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Financial profile not found. Please create your profile first.",
        )

    return foir_service.calculate_foir_from_profile(
        profile=profile,
        configured_threshold=threshold,
        proposed_emi=proposed_emi,
    )
