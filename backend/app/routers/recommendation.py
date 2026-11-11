"""
app/routers/recommendation.py
─────────────────────────────
HTTP router for the Personalized Loan Recommendation Engine.

Endpoints:
- POST /api/v1/recommendations/generate -> Generate tailored borrowing scenarios,
                                            prudent sizing, and eligibility assessments.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.models.user import User
from app.schemas.recommendation import (
    RecommendationRequest,
    RecommendationResponse,
)
from app.services import profile_service, recommendation_service

router = APIRouter(prefix="/recommendations", tags=["Loan Recommendations"])


@router.post(
    "/generate",
    response_model=RecommendationResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate personalized loan recommendations based on verified affordability",
)
async def generate_recommendations(
    body: Optional[RecommendationRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RecommendationResponse:
    """
    Generate personalized loan recommendations across 4 major loan categories:
    Personal, Home, Vehicle, and Education loans.

    - Authenticated access required via HTTP-only session cookie.
    - Uses caller's financial profile from the database (income, expenses, EMIs, savings, employment).
    - Returns HTTP 404 if the user has not yet initialized a financial profile.
    - Evaluates:
        * Theoretical capacity under configured FOIR benchmark
        * Prudent maximum monthly EMI based on disposable cash flow and risk safety buffers
        * Sizing and reducing-balance math for standard tenure benchmarks
        * Sizing against user requested loan amount or tenure if specified
    - Returns structured eligibility summary, risk considerations, and non-approval disclaimers.
    - Pure in-memory deterministic calculation; does not write to the database.
    """
    profile = await profile_service.get_profile_by_user_id(db, current_user.id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Financial profile not found. Please create your profile first.",
        )

    return recommendation_service.generate_loan_recommendations(
        profile=profile,
        request_params=body,
    )
