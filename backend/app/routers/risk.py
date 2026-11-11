"""
app/routers/risk.py
───────────────────
HTTP router for Financial Risk Assessment and Advisory Engine.

Endpoints:
- GET /api/v1/risk/assessment -> Evaluate multi-dimensional risk scores, diagnostic indicators,
                                 and actionable financial recommendations for the authenticated user.
"""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.models.user import User
from app.schemas.risk import RiskAssessmentResponse
from app.services import profile_service, risk_service

router = APIRouter(prefix="/risk", tags=["Risk & Advisory Engine"])


@router.get(
    "/assessment",
    response_model=RiskAssessmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get comprehensive financial risk assessment and advisory recommendations",
)
async def get_risk_assessment(
    threshold: Decimal = Query(
        Decimal("40.00"),
        ge=Decimal("1.00"),
        le=Decimal("100.00"),
        description="Configured FOIR policy benchmark percentage (default: 40.00%)",
        examples=[Decimal("40.00")],
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RiskAssessmentResponse:
    """
    Generate deterministic multi-factor financial risk analysis using the user's financial profile.

    - Authenticated access strictly required via HTTP-only session cookie.
    - Retrieves caller's profile from database. Returns 404 if not found.
    - Analyzes:
        * FOIR debt burden relative to configured policy threshold
        * Emergency reserve coverage in months (savings / expenses)
        * Disposable monthly income buffer (never hides negative cash flow)
        * Overleveraging policy flags
    - Produces transparent weighted risk score (0–100) and classification (LOW, MODERATE, HIGH, CRITICAL).
    - Generates actionable, tailored financial recommendations with priority ratings.
    - Pure in-memory deterministic calculation; does not write to DB.
    """
    profile = await profile_service.get_profile_by_user_id(db, current_user.id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Financial profile not found. Please create your profile first.",
        )

    return risk_service.assess_profile_risk(
        profile=profile,
        configured_threshold=threshold,
    )
