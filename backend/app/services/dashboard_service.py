"""
app/services/dashboard_service.py
─────────────────────────────────
Unified Financial Dashboard & Financial Health Score Engine.

Guarantees:
- 100% deterministic calculations using Python Decimal for financial precision.
- Implements the multi-factor weighted Financial Health Score defined in the architecture:
    Score = (0.35 * S_FOIR) + (0.30 * S_DebtBurden) + (0.20 * S_Emergency) + (0.15 * S_Savings)
- Aggregates verified outputs from Profile, FOIR, Risk, and Recommendation services.
- Never invents financial data; handles incomplete profiles gracefully.
"""

import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financial_profile import FinancialProfile
from app.schemas.dashboard import (
    DashboardMetricCards,
    DashboardSummaryResponse,
    FinancialHealthScore,
    HealthGradeEnum,
    HealthSubScoreItem,
)
from app.schemas.recommendation import RecommendationRequest
from app.services import (
    foir_service,
    profile_service,
    recommendation_service,
    risk_service,
)

CENT = Decimal("0.01")
ZERO = Decimal("0.00")
HUNDRED = Decimal("100.00")


def _calculate_foir_sub_score(foir: Decimal, income: Decimal = HUNDRED) -> Decimal:
    """
    Sub-score 1 (35% weight): Fixed Obligation to Income Ratio (FOIR).
    - Zero/negative income: 0.00 points (cannot service debt)
    - FOIR <= 30%: 100.00 points (Optimal debt load)
    - 30% < FOIR <= 60%: Linear degradation from 100.00 down to 0.00
    - FOIR > 60%: 0.00 points (Critical overleveraging)
    """
    if income <= ZERO:
        return ZERO
    if foir <= Decimal("30.00"):
        return HUNDRED
    if foir >= Decimal("60.00"):
        return ZERO

    # Linear interpolation: score = ((60 - foir) / 30) * 100
    points = ((Decimal("60.00") - foir) / Decimal("30.00")) * HUNDRED
    return max(ZERO, min(HUNDRED, points)).quantize(CENT, rounding=ROUND_HALF_UP)


def _calculate_debt_burden_sub_score(
    income: Decimal,
    existing_emi: Decimal,
    disposable_income: Decimal,
    loan_count: int,
) -> Decimal:
    """
    Sub-score 2 (30% weight): Debt Burden, Cash Flow Sufficiency & Loan Count.
    - Zero/negative income: 0 points (cannot service debt)
    - Cash deficit (disposable income < 0): 0 points
    - Zero debt: 100 points
    - DTI <= 20%: 90 - 100 points
    - High active loan count (> 3 loans): -10 penalty per excess loan
    """
    if income <= ZERO:
        return ZERO

    if disposable_income < ZERO:
        return ZERO

    if existing_emi <= ZERO:
        base_score = HUNDRED
    else:
        dti = (existing_emi / income) * HUNDRED
        if dti <= Decimal("20.00"):
            base_score = HUNDRED - (dti * Decimal("0.50"))
        elif dti <= Decimal("50.00"):
            # Linear scale from 90 down to 20
            base_score = Decimal("90.00") - (((dti - Decimal("20.00")) / Decimal("30.00")) * Decimal("70.00"))
        else:
            base_score = max(ZERO, Decimal("20.00") - (dti - Decimal("50.00")))

    # Active loan count penalty (> 3 loans indicates potential credit fragmentation)
    penalty = ZERO
    if loan_count > 3:
        penalty = min(Decimal("30.00"), Decimal(str(loan_count - 3)) * Decimal("10.00"))

    final_score = max(ZERO, base_score - penalty)
    return min(HUNDRED, final_score).quantize(CENT, rounding=ROUND_HALF_UP)


def _calculate_emergency_fund_sub_score(
    savings: Decimal,
    expenses: Decimal,
) -> Decimal:
    """
    Sub-score 3 (20% weight): Emergency Fund Depth (in months of living expenses).
    - >= 6.0 months: 100 points (Golden standard)
    - 3.0 to 5.9 months: 60 - 99 points (Adequate reserve)
    - 1.0 to 2.9 months: 20 - 59 points (Vulnerable buffer)
    - < 1.0 month: 0 - 19 points (Severe liquidity risk)
    """
    if expenses <= ZERO:
        return HUNDRED if savings > ZERO else ZERO

    coverage = savings / expenses
    if coverage >= Decimal("6.00"):
        return HUNDRED
    if coverage >= Decimal("3.00"):
        score = Decimal("60.00") + (((coverage - Decimal("3.00")) / Decimal("3.00")) * Decimal("40.00"))
    elif coverage >= Decimal("1.00"):
        score = Decimal("20.00") + (((coverage - Decimal("1.00")) / Decimal("2.00")) * Decimal("40.00"))
    else:
        score = coverage * Decimal("20.00")

    return max(ZERO, min(HUNDRED, score)).quantize(CENT, rounding=ROUND_HALF_UP)


def _calculate_savings_reserve_sub_score(
    savings: Decimal,
    monthly_income: Decimal,
) -> Decimal:
    """
    Sub-score 4 (15% weight): Savings Reserve Ratio Score (Capital relative to Annual Income).
    - Total liquid savings >= 20% of annual net income: 100 points
    - Below 20%: Scales linearly from 0 up to 100
    """
    annual_income = monthly_income * Decimal("12.00")
    if annual_income <= ZERO:
        return ZERO

    savings_ratio = (savings / annual_income) * HUNDRED
    if savings_ratio >= Decimal("20.00"):
        return HUNDRED

    score = (savings_ratio / Decimal("20.00")) * HUNDRED
    return max(ZERO, min(HUNDRED, score)).quantize(CENT, rounding=ROUND_HALF_UP)


def compute_financial_health_score(profile: FinancialProfile) -> FinancialHealthScore:
    """
    Compute deterministic composite Financial Health Score and breakdown.
    Formula:
        Score = (0.35 * S_FOIR) + (0.30 * S_Debt) + (0.20 * S_Emergency) + (0.15 * S_Savings)
    """
    income = Decimal(str(profile.monthly_net_income))
    expenses = Decimal(str(profile.monthly_expenses))
    existing_emi = Decimal(str(profile.existing_monthly_emi))
    savings = Decimal(str(profile.emergency_savings))
    loan_count = profile.existing_loan_count or 0

    if income > ZERO:
        foir = (existing_emi / income * HUNDRED).quantize(CENT, rounding=ROUND_HALF_UP)
    else:
        foir = HUNDRED if existing_emi > ZERO else ZERO

    disposable_income = income - expenses - existing_emi

    # 1. Individual Sub-scores
    s_foir = _calculate_foir_sub_score(foir, income)
    s_debt = _calculate_debt_burden_sub_score(income, existing_emi, disposable_income, loan_count)
    s_emergency = _calculate_emergency_fund_sub_score(savings, expenses)
    s_savings = _calculate_savings_reserve_sub_score(savings, income)

    # 2. Weights and Contributions
    w_foir = Decimal("0.35")
    w_debt = Decimal("0.30")
    w_emergency = Decimal("0.20")
    w_savings = Decimal("0.15")

    c_foir = (s_foir * w_foir).quantize(CENT, rounding=ROUND_HALF_UP)
    c_debt = (s_debt * w_debt).quantize(CENT, rounding=ROUND_HALF_UP)
    c_emergency = (s_emergency * w_emergency).quantize(CENT, rounding=ROUND_HALF_UP)
    c_savings = (s_savings * w_savings).quantize(CENT, rounding=ROUND_HALF_UP)

    overall_score = (c_foir + c_debt + c_emergency + c_savings).quantize(CENT, rounding=ROUND_HALF_UP)
    overall_score = max(ZERO, min(HUNDRED, overall_score))

    # 3. Determine Letter Grade and Qualitative Status
    if overall_score >= Decimal("85.00"):
        letter_grade = HealthGradeEnum.A_PLUS
        status_label = "Optimal Financial Health"
        summary = "Exceptional debt management, strong liquid reserves, and substantial borrowing headroom."
    elif overall_score >= Decimal("70.00"):
        letter_grade = HealthGradeEnum.A
        status_label = "Strong Financial Stability"
        summary = "Well-balanced debt obligations and healthy living surplus with robust emergency coverage."
    elif overall_score >= Decimal("55.00"):
        letter_grade = HealthGradeEnum.B
        status_label = "Manageable Financial Position"
        summary = "Moderate debt obligations with room for financial growth. Prioritize emergency fund building."
    elif overall_score >= Decimal("40.00"):
        letter_grade = HealthGradeEnum.C
        status_label = "Elevated Debt / Stretched Reserves"
        summary = "Debt servicing is consuming a significant portion of earnings. Exercise caution with new credit."
    elif overall_score >= Decimal("25.00"):
        letter_grade = HealthGradeEnum.D
        status_label = "High Debt Vulnerability"
        summary = "High fixed obligations with limited safety margins. Focus aggressively on debt paydown."
    else:
        letter_grade = HealthGradeEnum.F
        status_label = "Severe Financial Distress"
        summary = "Critical overleveraging or monthly deficit detected. Immediate debt restructuring advised."

    # Sub-score items with qualitative status
    if income <= ZERO:
        if existing_emi <= ZERO:
            foir_status_str = "No Debt"
            foir_detail_str = "No active loan obligations reported. Net income is zero or non-positive, preventing debt-to-income evaluation."
        else:
            foir_status_str = "Critical"
            foir_detail_str = f"Fixed obligations consume 100.0% of net income with ₹{existing_emi:,.2f} in active monthly EMIs (target <= 30%)."
    else:
        foir_detail_str = f"Fixed obligations consume {foir:.1f}% of net income (target <= 30%)."
        if s_foir >= Decimal("80.00"):
            foir_status_str = "Optimal"
        elif s_foir >= Decimal("50.00"):
            foir_status_str = "Moderate"
        elif s_foir > Decimal("0.00"):
            foir_status_str = "Stretched"
        else:
            foir_status_str = "Critical"

    sub_scores: List[HealthSubScoreItem] = [
        HealthSubScoreItem(
            name="FOIR Debt Ratio",
            score=s_foir,
            weight_percentage=Decimal("35.00"),
            weighted_score=c_foir,
            status=foir_status_str,
            detail=foir_detail_str,
        ),
        HealthSubScoreItem(
            name="Debt Burden & Loan Count",
            score=s_debt,
            weight_percentage=Decimal("30.00"),
            weighted_score=c_debt,
            status="Optimal" if s_debt >= Decimal("80.00") else "Moderate" if s_debt >= Decimal("50.00") else "Vulnerable",
            detail=f"Monthly EMI: ₹{existing_emi:,.2f} across {loan_count} active loan(s).",
        ),
        HealthSubScoreItem(
            name="Emergency Fund Adequacy",
            score=s_emergency,
            weight_percentage=Decimal("20.00"),
            weighted_score=c_emergency,
            status="Optimal" if s_emergency >= Decimal("80.00") else "Adequate" if s_emergency >= Decimal("50.00") else "Critical",
            detail=f"Liquid reserves cover {((savings / expenses) if expenses > ZERO else Decimal('0.00')):.1f} months of living costs (target >= 6 months).",
        ),
        HealthSubScoreItem(
            name="Savings Reserve Ratio Score",
            score=s_savings,
            weight_percentage=Decimal("15.00"),
            weighted_score=c_savings,
            status="Optimal" if s_savings >= Decimal("80.00") else "Moderate" if s_savings >= Decimal("50.00") else "Low",
            detail=f"Emergency savings represent {((savings / (income * Decimal('12.00'))) * HUNDRED if income > ZERO else Decimal('0.00')):.1f}% of annual earnings (target >= 20%).",
        ),
    ]

    return FinancialHealthScore(
        overall_score=overall_score,
        letter_grade=letter_grade,
        status_label=status_label,
        summary=summary,
        sub_scores=sub_scores,
    )


async def get_dashboard_summary(
    db: AsyncSession,
    user_id: uuid.UUID,
    foir_threshold: Decimal = Decimal("40.00"),
) -> DashboardSummaryResponse:
    """
    Retrieve or aggregate the complete financial dashboard overview for the authenticated user.
    """
    profile = await profile_service.get_profile_by_user_id(db, user_id)

    # 1. Clean handling for users who have not yet initialized their profile
    if profile is None:
        return DashboardSummaryResponse(
            profile_complete=False,
            active_warnings=[
                "Financial profile not yet initialized. Please complete your profile to unlock personalized health scoring, risk metrics, and loan recommendations."
            ],
            actionable_highlights=[
                "Navigate to 'Profile & Settings' to enter your income, monthly living expenses, and existing loan details."
            ],
        )

    # 2. Compute Financial Health Score
    health_score = compute_financial_health_score(profile)

    # 3. Retrieve verified FOIR calculations
    foir_data = foir_service.calculate_foir_from_profile(profile, foir_threshold)

    # 4. Retrieve multi-factor Risk assessment
    risk_data = risk_service.assess_profile_risk(profile, foir_threshold)

    # 5. Retrieve Personalized Loan Recommendations
    rec_request = RecommendationRequest(foir_threshold=foir_threshold)
    rec_data = recommendation_service.generate_loan_recommendations(profile, rec_request)

    # 6. Core Metric Cards
    income = Decimal(str(profile.monthly_net_income))
    expenses = Decimal(str(profile.monthly_expenses))
    existing_emi = Decimal(str(profile.existing_monthly_emi))
    savings = Decimal(str(profile.emergency_savings))
    loan_count = profile.existing_loan_count or 0
    disposable_income = income - expenses - existing_emi
    coverage_months = (savings / expenses).quantize(CENT, rounding=ROUND_HALF_UP) if expenses > ZERO else ZERO

    metrics = DashboardMetricCards(
        monthly_net_income=income,
        total_active_loans=loan_count,
        monthly_emi_burden=existing_emi,
        monthly_living_expenses=expenses,
        disposable_monthly_cash_flow=disposable_income,
        emergency_fund_months=coverage_months,
        emergency_savings_total=savings,
        prudent_max_monthly_emi=rec_data.financial_snapshot.prudent_max_monthly_emi,
    )

    # 7. Actionable highlights & alerts consolidation
    active_warnings: List[str] = list(risk_data.triggered_warnings)
    if not rec_data.is_eligible and rec_data.reasons_and_warnings:
        for w in rec_data.reasons_and_warnings:
            if w not in active_warnings:
                active_warnings.append(w)

    actionable_highlights: List[str] = []
    if risk_data.recommendations:
        for r in risk_data.recommendations[:3]:
            actionable_highlights.append(f"[{r.priority.value}] {r.title}: {r.suggested_action}")

    top_rec = ""
    if rec_data.is_eligible and rec_data.recommendations:
        top_rec = (
            f"You are eligible for up to ₹{rec_data.financial_snapshot.prudent_max_monthly_emi:,.2f}/month in prudent EMI capacity. "
            f"Top recommended option: {rec_data.recommendations[0].category_display_name} up to ₹{rec_data.recommendations[0].recommended_principal:,.2f}."
        )
    else:
        top_rec = rec_data.eligibility_summary

    return DashboardSummaryResponse(
        profile_complete=True,
        health_score=health_score,
        metrics=metrics,
        current_foir_percentage=foir_data.current_foir_percentage,
        foir_status=foir_data.affordability_status.value,
        overall_risk_category=risk_data.overall_risk_category.value,
        overall_risk_score=risk_data.overall_risk_score,
        is_borrowing_eligible=rec_data.is_eligible,
        prudent_max_borrowing_emi=rec_data.financial_snapshot.prudent_max_monthly_emi,
        top_recommendation_summary=top_rec,
        active_warnings=active_warnings,
        actionable_highlights=actionable_highlights,
    )
