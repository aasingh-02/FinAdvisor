"""
app/routers/dashboard.py
────────────────────────
HTTP router for the Unified Financial Dashboard & Financial Health Score API.

Provides:
- GET /api/v1/dashboard -> Comprehensive overview aggregating health score, FOIR, risk diagnostics, and borrowing capacity.
Protected by HTTP-only cookie session authentication.
"""

from decimal import Decimal
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.models.user import User
from app.schemas.dashboard import DashboardSummaryResponse
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "",
    response_model=DashboardSummaryResponse,
    summary="Get aggregated financial dashboard overview and health score",
)
async def get_dashboard(
    threshold: float = Query(
        default=40.0,
        ge=1.0,
        le=100.0,
        description="Configurable FOIR policy threshold benchmark (1.0 to 100.0%)",
        examples=[40.0],
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardSummaryResponse:
    """
    Retrieve the aggregated financial health overview for the authenticated user.
    If the user has not completed their financial profile, returns a clean profile_complete=False response.
    """
    foir_threshold_dec = Decimal(str(threshold))
    return await dashboard_service.get_dashboard_summary(
        db=db,
        user_id=current_user.id,
        foir_threshold=foir_threshold_dec,
    )
