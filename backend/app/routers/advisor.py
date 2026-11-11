"""
app/routers/advisor.py
──────────────────────
HTTP router for the AI Financial Advisor & Copilot engine.

Endpoints:
- POST /api/v1/advisor/chat    -> Context-aware conversational AI advisory chat.
- POST /api/v1/advisor/explain -> Deep dive explanation of specific financial metrics / simulation results.

Guarantees & Security:
- Protected by HTTP-only session cookie authentication (get_current_user).
- Enforces strict multi-tenant isolation: queries only the authenticated user's financial profile.
- All factual financial numbers are computed deterministically and returned separately.
- Zero PII is transmitted to external AI providers.
"""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.models.user import User
from app.schemas.advisor import (
    AdvisorChatRequest,
    AdvisorExplainRequest,
    AdvisorResponse,
)
from app.services import ai_advisor_service
from app.utils.rate_limit import get_user_or_ip_key, limiter

router = APIRouter(prefix="/advisor", tags=["AI Advisor"])


@router.post(
    "/chat",
    response_model=AdvisorResponse,
    status_code=status.HTTP_200_OK,
    summary="Interactive AI Financial Advisor Chat",
    description=(
        "Submit a user query to FinAdvisor's AI Financial Copilot. Grounded on deterministic "
        "profile and dashboard figures (FOIR, Health Score, Risk Category). Never exposes PII."
    ),
)
@limiter.limit("30/minute", key_func=get_user_or_ip_key)
async def advisor_chat(
    request: Request,
    body: AdvisorChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AdvisorResponse:
    """
    Process context-aware advisory chat for the authenticated user.
    """
    return await ai_advisor_service.generate_advisor_chat_response(
        db=db,
        user_id=current_user.id,
        request=body,
    )


@router.post(
    "/explain",
    response_model=AdvisorResponse,
    status_code=status.HTTP_200_OK,
    summary="AI Explanation for Specific Financial Metric",
    description=(
        "Obtain clear, personalized educational breakdown of a specific financial component "
        "(HEALTH_SCORE, FOIR_AFFORDABILITY, RISK_ASSESSMENT, LOAN_RECOMMENDATIONS, EMI_SIMULATION)."
    ),
)
async def advisor_explain(
    request: AdvisorExplainRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AdvisorResponse:
    """
    Generate deep-dive explanation for a specific financial indicator.
    """
    return await ai_advisor_service.generate_advisor_explanation(
        db=db,
        user_id=current_user.id,
        request=request,
    )
