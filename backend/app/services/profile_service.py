"""
app/services/profile_service.py
───────────────────────────────
Business logic for managing user financial profiles.

Guarantees:
- All database queries are strictly scoped to the authenticated user's ID.
- Users cannot access, create, or modify another user's financial profile.
- Handles atomic creation, retrieval, full upserts, and partial PATCH updates.
- Uses proper transaction rollback semantics on exceptions.
"""

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financial_profile import FinancialProfile
from app.schemas.financial_profile import FinancialProfileCreate, FinancialProfileUpdate


async def get_profile_by_user_id(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> Optional[FinancialProfile]:
    """
    Retrieve the financial profile strictly belonging to user_id.
    Returns None if no profile has been created yet.
    """
    stmt = select(FinancialProfile).where(FinancialProfile.user_id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def upsert_profile(
    db: AsyncSession,
    user_id: uuid.UUID,
    data: FinancialProfileCreate,
) -> FinancialProfile:
    """
    Create a new financial profile or fully replace the existing one for user_id.
    """
    try:
        profile = await get_profile_by_user_id(db, user_id)

        if profile is None:
            # Create fresh profile
            profile = FinancialProfile(
                user_id=user_id,
                monthly_net_income=data.monthly_net_income,
                monthly_expenses=data.monthly_expenses,
                existing_monthly_emi=data.existing_monthly_emi,
                emergency_savings=data.emergency_savings,
                employment_type=data.employment_type.value,
                existing_loan_count=data.existing_loan_count,
            )
            db.add(profile)
        else:
            # Update existing profile
            profile.monthly_net_income = data.monthly_net_income
            profile.monthly_expenses = data.monthly_expenses
            profile.existing_monthly_emi = data.existing_monthly_emi
            profile.emergency_savings = data.emergency_savings
            profile.employment_type = data.employment_type.value
            profile.existing_loan_count = data.existing_loan_count

        await db.flush()
        await db.refresh(profile)
        return profile
    except Exception:
        await db.rollback()
        raise


async def update_profile(
    db: AsyncSession,
    user_id: uuid.UUID,
    data: FinancialProfileUpdate,
) -> FinancialProfile:
    """
    Partially update a financial profile using exclude_unset=True.

    Raises:
        ValueError: if the profile does not exist, no fields are provided,
                    or any field value is explicitly null.
    """
    # 1. Reject empty payload
    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise ValueError("No fields provided for update.")

    # 2. Reject explicit nulls
    for field_name, value in update_data.items():
        if value is None:
            raise ValueError(f"Field '{field_name}' cannot be null.")

    # 3. Retrieve user profile
    profile = await get_profile_by_user_id(db, user_id)
    if profile is None:
        raise ValueError("Financial profile not found. Please create a profile first.")

    try:
        # 4. Apply updates
        for field_name, value in update_data.items():
            if field_name == "employment_type" and hasattr(value, "value"):
                setattr(profile, field_name, value.value)
            elif field_name == "employment_type" and isinstance(value, str):
                setattr(profile, field_name, value)
            else:
                setattr(profile, field_name, value)

        await db.flush()
        await db.refresh(profile)
        return profile
    except Exception:
        await db.rollback()
        raise
