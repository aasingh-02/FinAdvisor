"""
app/routers/profile.py
──────────────────────
HTTP router for User Financial Profile management.

Endpoints:
- GET   /api/v1/profile  -> View current user's profile (404 if not yet created)
- PUT   /api/v1/profile  -> Create or replace current user's profile
- PATCH /api/v1/profile  -> Partially update current user's profile
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.models.user import User
from app.schemas.financial_profile import (
    FinancialProfileCreate,
    FinancialProfileResponse,
    FinancialProfileUpdate,
    ProfileMessageResponse,
)
from app.services import profile_service

router = APIRouter(prefix="/profile", tags=["Financial Profile"])


@router.get(
    "",
    response_model=FinancialProfileResponse,
    summary="Get current user's financial profile",
)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FinancialProfileResponse:
    """
    Fetch the authenticated user's financial profile.
    Returns HTTP 404 if the user has not yet initialized a profile.
    """
    profile = await profile_service.get_profile_by_user_id(db, current_user.id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Financial profile not found. Please create your profile first.",
        )
    return FinancialProfileResponse.model_validate(profile)


@router.put(
    "",
    response_model=ProfileMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Create or replace current user's financial profile",
)
async def upsert_my_profile(
    body: FinancialProfileCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProfileMessageResponse:
    """
    Create or completely overwrite the authenticated user's financial profile.
    Guarantees the profile is securely bound to the authenticated user's ID.
    """
    try:
        profile = await profile_service.upsert_profile(
            db=db,
            user_id=current_user.id,
            data=body,
        )
        return ProfileMessageResponse(
            message="Financial profile saved successfully.",
            profile=FinancialProfileResponse.model_validate(profile),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.patch(
    "",
    response_model=ProfileMessageResponse,
    summary="Partially update current user's financial profile",
)
async def patch_my_profile(
    body: FinancialProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProfileMessageResponse:
    """
    Partially update fields in the user's financial profile.
    Requires at least one field to be provided. Explicit nulls are rejected.
    """
    try:
        profile = await profile_service.update_profile(
            db=db,
            user_id=current_user.id,
            data=body,
        )
        return ProfileMessageResponse(
            message="Financial profile updated successfully.",
            profile=FinancialProfileResponse.model_validate(profile),
        )
    except ValueError as exc:
        error_msg = str(exc)
        status_code = (
            status.HTTP_404_NOT_FOUND
            if "not found" in error_msg.lower()
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(
            status_code=status_code,
            detail=error_msg,
        )
