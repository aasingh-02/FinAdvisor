"""
app/services/risk_service.py
────────────────────────────
Deterministic Financial Risk Assessment and Advisory Engine.

Methodology:
- Evaluates 4 multi-dimensional financial health indicators:
  1. FOIR / Debt Burden (Weight: 40%)
  2. Emergency Fund Adequacy (Weight: 30%)
  3. Disposable Monthly Cash Flow (Weight: 20%)
  4. Policy Overleveraging Status (Weight: 10%)
- Produces individual indicator scores (0.00 - 100.00) and weighted overall score.
- Categorizes risk into transparent tiers: LOW, MODERATE, HIGH, CRITICAL.
- Generates specific, non-generic actionable recommendations with explicit urgency levels.
- Strictly uses Python Decimal arithmetic with ROUND_HALF_UP precision.
- Fully deterministic; never relies on black-box heuristics or hardcoded mock figures.
"""

from decimal import Decimal, ROUND_HALF_UP, getcontext
from typing import List, Optional, Tuple

from app.models.financial_profile import FinancialProfile
from app.schemas.risk import (
    AdvisoryRecommendation,
    RecommendationPriorityEnum,
    RiskAssessmentResponse,
    RiskIndicatorDetail,
    RiskLevelEnum,
)
from app.services import foir_service

# Math Constants
CENT = Decimal("0.01")
ZERO = Decimal("0.00")
HUNDRED = Decimal("100.00")

# Default Weights
WEIGHT_FOIR = Decimal("0.40")
WEIGHT_EMERGENCY = Decimal("0.30")
WEIGHT_DISPOSABLE = Decimal("0.20")
WEIGHT_OVERLEVERAGED = Decimal("0.10")

DISCLAIMER_TEXT = (
    "This assessment is an illustrative personal financial health analysis based on self-reported profile data. "
    "It is not a credit bureau score (e.g. CIBIL/Experian), formal lender underwriting evaluation, or loan approval guarantee."
)


def evaluate_foir_indicator(
    current_foir: Decimal,
    threshold: Decimal,
    income: Decimal,
) -> Tuple[Decimal, RiskLevelEnum, str, str]:
    """
    Evaluate debt burden based on FOIR percentage.
    Returns: (score, risk_level, value_display, explanation)
    """
    if income <= ZERO:
        return (
            HUNDRED,
            RiskLevelEnum.CRITICAL,
            f"{current_foir:.2f}%",
            "Monthly net income is reported as zero or non-positive. Debt burden is critical.",
        )

    val_str = f"{current_foir:.2f}%"

    if current_foir <= Decimal("20.00"):
        # Very low debt: score 0 to 15
        score = (current_foir / Decimal("20.00")) * Decimal("15.00")
        level = RiskLevelEnum.LOW
        exp = f"FOIR of {val_str} is very conservative, leaving ample debt capacity."
    elif current_foir <= threshold:
        # Manageable debt: score 15 to 40
        span = threshold - Decimal("20.00")
        prog = (current_foir - Decimal("20.00")) / span if span > ZERO else ZERO
        score = Decimal("15.00") + prog * Decimal("25.00")
        level = RiskLevelEnum.MODERATE
        exp = f"FOIR of {val_str} is within your {threshold:.1f}% policy threshold. Debt commitments are manageable."
    elif current_foir <= Decimal("55.00"):
        # Stretched debt: score 40 to 75
        span = Decimal("55.00") - threshold
        prog = (current_foir - threshold) / span if span > ZERO else ZERO
        score = Decimal("40.00") + prog * Decimal("35.00")
        level = RiskLevelEnum.HIGH
        exp = f"FOIR of {val_str} exceeds your {threshold:.1f}% policy threshold. Fixed debt commitments are stretched."
    else:
        # Critical debt: score 75 to 100
        extra = current_foir - Decimal("55.00")
        prog = min(Decimal("1.00"), extra / Decimal("15.00"))
        score = Decimal("75.00") + prog * Decimal("25.00")
        level = RiskLevelEnum.CRITICAL
        exp = f"FOIR of {val_str} is critically elevated. Over half of your net income is committed to loan repayments."

    score = max(ZERO, min(HUNDRED, score.quantize(CENT, rounding=ROUND_HALF_UP)))
    return (score, level, val_str, exp)


def evaluate_emergency_fund_indicator(
    savings: Decimal,
    expenses: Decimal,
) -> Tuple[Decimal, Decimal, RiskLevelEnum, str, str]:
    """
    Evaluate emergency reserve coverage in months.
    Returns: (score, coverage_months, risk_level, value_display, explanation)
    """
    if expenses > ZERO:
        coverage = (savings / expenses).quantize(CENT, rounding=ROUND_HALF_UP)
    else:
        # Zero monthly expenses reported
        coverage = Decimal("12.00") if savings > ZERO else ZERO

    val_str = f"{coverage:.2f} months"

    if expenses <= ZERO and savings > ZERO:
        score = ZERO
        level = RiskLevelEnum.LOW
        exp = f"Reported savings of ₹{savings:,.2f} with zero reported monthly expenses represents a solid reserve buffer."
    elif coverage >= Decimal("6.00"):
        # Healthy: >= 6 months
        score = max(ZERO, Decimal("15.00") - (coverage - Decimal("6.00")) * Decimal("2.00"))
        level = RiskLevelEnum.LOW
        exp = f"Emergency reserve provides {val_str} of living expenses, satisfying the recommended 6-month buffer."
    elif coverage >= Decimal("3.00"):
        # Moderate: 3 to 6 months
        prog = (Decimal("6.00") - coverage) / Decimal("3.00")
        score = Decimal("20.00") + prog * Decimal("30.00")
        level = RiskLevelEnum.MODERATE
        exp = f"Emergency fund covers {val_str} of expenses. Moderate buffer; consider bolstering to 6 months."
    elif coverage >= Decimal("1.00"):
        # Low: 1 to 3 months
        prog = (Decimal("3.00") - coverage) / Decimal("2.00")
        score = Decimal("55.00") + prog * Decimal("25.00")
        level = RiskLevelEnum.HIGH
        exp = f"Emergency fund covers only {val_str} of expenses. Low cushion against sudden income disruption."
    else:
        # Inadequate: < 1 month
        prog = Decimal("1.00") - min(Decimal("1.00"), coverage)
        score = Decimal("85.00") + prog * Decimal("15.00")
        level = RiskLevelEnum.CRITICAL
        exp = f"Emergency fund covers only {val_str} of expenses. Severe vulnerability to unexpected costs."

    score = max(ZERO, min(HUNDRED, score.quantize(CENT, rounding=ROUND_HALF_UP)))
    return (score, coverage, level, val_str, exp)


def evaluate_disposable_income_indicator(
    income: Decimal,
    expenses: Decimal,
    existing_emi: Decimal,
) -> Tuple[Decimal, Decimal, RiskLevelEnum, str, str]:
    """
    Evaluate monthly disposable cash flow.
    Returns: (score, disposable_income, risk_level, value_display, explanation)
    """
    disposable = (income - expenses - existing_emi).quantize(CENT, rounding=ROUND_HALF_UP)
    val_str = f"₹{disposable:,.2f}"

    if income <= ZERO:
        return (
            HUNDRED,
            disposable,
            RiskLevelEnum.CRITICAL,
            val_str,
            "Net income is reported as zero or non-positive. Monthly cash flow cannot sustain debt.",
        )

    ratio = (disposable / income) * HUNDRED

    if disposable < ZERO:
        score = HUNDRED
        level = RiskLevelEnum.CRITICAL
        exp = f"Cash flow deficit of {val_str}. Monthly commitments (EMIs + expenses) exceed your monthly net income."
    elif ratio < Decimal("10.00"):
        prog = (Decimal("10.00") - ratio) / Decimal("10.00")
        score = Decimal("60.00") + prog * Decimal("25.00")
        level = RiskLevelEnum.HIGH
        exp = f"Remaining disposable income is thin at {val_str} ({ratio:.1f}% of net income). Limited flexibility for contingencies."
    elif ratio < Decimal("25.00"):
        prog = (Decimal("25.00") - ratio) / Decimal("15.00")
        score = Decimal("25.00") + prog * Decimal("30.00")
        level = RiskLevelEnum.MODERATE
        exp = f"Disposable income of {val_str} ({ratio:.1f}% of net income) provides moderate buffer for routine savings."
    else:
        score = ZERO
        level = RiskLevelEnum.LOW
        exp = f"Healthy disposable income of {val_str} ({ratio:.1f}% of net income) provides strong personal cash flow cushion."

    score = max(ZERO, min(HUNDRED, score.quantize(CENT, rounding=ROUND_HALF_UP)))
    return (score, disposable, level, val_str, exp)


def evaluate_overleveraging_indicator(
    existing_emi: Decimal,
    max_permissible_emi: Decimal,
    threshold: Decimal,
) -> Tuple[Decimal, RiskLevelEnum, str, str]:
    """
    Evaluate whether existing debt obligations exceed configured policy headroom.
    Returns: (score, risk_level, value_display, explanation)
    """
    if existing_emi > max_permissible_emi:
        excess = existing_emi - max_permissible_emi
        score = HUNDRED
        level = RiskLevelEnum.CRITICAL if excess > (max_permissible_emi * Decimal("0.20")) else RiskLevelEnum.HIGH
        val_str = f"Over limit by ₹{excess:,.2f}"
        exp = (
            f"Existing EMIs (₹{existing_emi:,.2f}) exceed the {threshold:.1f}% policy limit of "
            f"₹{max_permissible_emi:,.2f} by ₹{excess:,.2f}. No additional borrowing capacity remains under this policy."
        )
    else:
        headroom = max_permissible_emi - existing_emi
        score = ZERO
        level = RiskLevelEnum.LOW
        val_str = f"Within limit (₹{headroom:,.2f} headroom)"
        exp = (
            f"Existing monthly loan commitments are within your configured {threshold:.1f}% benchmark. "
            f"You retain ₹{headroom:,.2f} in theoretical additional monthly borrowing capacity."
        )

    return (score, level, val_str, exp)


def assess_profile_risk(
    profile: FinancialProfile,
    configured_threshold: Decimal = Decimal("40.00"),
) -> RiskAssessmentResponse:
    """
    Execute full multi-dimensional deterministic risk assessment on the user's financial profile.
    """
    getcontext().prec = 35

    income = profile.monthly_net_income.quantize(CENT, rounding=ROUND_HALF_UP)
    existing_emi = profile.existing_monthly_emi.quantize(CENT, rounding=ROUND_HALF_UP)
    expenses = profile.monthly_expenses.quantize(CENT, rounding=ROUND_HALF_UP)
    savings = profile.emergency_savings.quantize(CENT, rounding=ROUND_HALF_UP)
    threshold = configured_threshold.quantize(CENT, rounding=ROUND_HALF_UP)

    # 1. Reuse existing deterministic FOIR service
    foir_result = foir_service.calculate_foir_from_profile(
        profile=profile,
        configured_threshold=threshold,
    )
    current_foir = foir_result.current_foir_percentage
    max_permissible_emi = foir_result.maximum_permissible_emi

    # 2. Evaluate Indicators
    s_foir, l_foir, v_foir, exp_foir = evaluate_foir_indicator(current_foir, threshold, income)
    s_emrg, cov_months, l_emrg, v_emrg, exp_emrg = evaluate_emergency_fund_indicator(savings, expenses)
    s_disp, disposable_inc, l_disp, v_disp, exp_disp = evaluate_disposable_income_indicator(income, expenses, existing_emi)
    s_over, l_over, v_over, exp_over = evaluate_overleveraging_indicator(existing_emi, max_permissible_emi, threshold)

    indicators: List[RiskIndicatorDetail] = [
        RiskIndicatorDetail(
            indicator_key="FOIR",
            indicator_name="Debt-to-Income Burden (FOIR)",
            score=s_foir,
            risk_level=l_foir,
            value_display=v_foir,
            explanation=exp_foir,
        ),
        RiskIndicatorDetail(
            indicator_key="EMERGENCY_FUND",
            indicator_name="Emergency Reserve Coverage",
            score=s_emrg,
            risk_level=l_emrg,
            value_display=v_emrg,
            explanation=exp_emrg,
        ),
        RiskIndicatorDetail(
            indicator_key="DISPOSABLE_INCOME",
            indicator_name="Disposable Monthly Cash Flow",
            score=s_disp,
            risk_level=l_disp,
            value_display=v_disp,
            explanation=exp_disp,
        ),
        RiskIndicatorDetail(
            indicator_key="OVERLEVERAGING",
            indicator_name="Policy Threshold Compliance",
            score=s_over,
            risk_level=l_over,
            value_display=v_over,
            explanation=exp_over,
        ),
    ]

    # 3. Overall Weighted Score Calculation
    raw_score = (
        (s_foir * WEIGHT_FOIR)
        + (s_emrg * WEIGHT_EMERGENCY)
        + (s_disp * WEIGHT_DISPOSABLE)
        + (s_over * WEIGHT_OVERLEVERAGED)
    )

    # Safety Overrides:
    # If in severe cash deficit or extreme FOIR (>70%), score must be at least 75.00 (Critical)
    if disposable_inc < ZERO or current_foir >= Decimal("70.00") or income <= ZERO:
        raw_score = max(Decimal("76.00"), raw_score)

    overall_score = max(ZERO, min(HUNDRED, raw_score.quantize(CENT, rounding=ROUND_HALF_UP)))

    # Overall Category Classification
    if overall_score <= Decimal("25.00"):
        overall_category = RiskLevelEnum.LOW
    elif overall_score <= Decimal("50.00"):
        overall_category = RiskLevelEnum.MODERATE
    elif overall_score <= Decimal("75.00"):
        overall_category = RiskLevelEnum.HIGH
    else:
        overall_category = RiskLevelEnum.CRITICAL

    # 4. Triggered Warnings
    warnings: List[str] = []
    if disposable_inc < ZERO:
        warnings.append(
            f"Monthly cash deficit detected: Your living expenses and loan payments exceed monthly net income by ₹{abs(disposable_inc):,.2f}."
        )
    if existing_emi > max_permissible_emi:
        warnings.append(
            f"Overleveraged relative to policy: Existing EMIs exceed the {threshold:.1f}% threshold by ₹{(existing_emi - max_permissible_emi):,.2f}."
        )
    if current_foir > Decimal("55.00"):
        warnings.append(
            f"Critical debt burden: Over half of your net monthly earnings ({current_foir:.1f}%) are consumed by existing loan EMIs."
        )
    if cov_months < Decimal("3.00") and expenses > ZERO:
        warnings.append(
            f"Inadequate emergency cushion: Liquid savings cover only {cov_months:.1f} months of expenses (recommended minimum is 3–6 months)."
        )
    if income <= ZERO:
        warnings.append("Reported monthly net income is zero or non-positive.")

    # 5. Targeted Actionable Recommendations
    recommendations: List[AdvisoryRecommendation] = []

    # Recommendation for Cash Deficit
    if disposable_inc < ZERO:
        recommendations.append(
            AdvisoryRecommendation(
                title="Resolve Cash Flow Deficit Immediately",
                explanation=(
                    f"Your fixed monthly obligations (₹{existing_emi:,.2f}) and household costs (₹{expenses:,.2f}) "
                    f"exceed net income (₹{income:,.2f}) by ₹{abs(disposable_inc):,.2f} per month."
                ),
                priority=RecommendationPriorityEnum.CRITICAL,
                related_indicator="DISPOSABLE_INCOME",
                suggested_action=(
                    "Implement immediate expense reduction, defer non-essential purchases, and contact lenders "
                    "for tenure restructuring or debt consolidation before considering any new credit."
                ),
            )
        )

    # Recommendation for Debt / FOIR
    if existing_emi > max_permissible_emi or current_foir > threshold:
        priority = (
            RecommendationPriorityEnum.CRITICAL
            if current_foir > Decimal("55.00")
            else RecommendationPriorityEnum.HIGH
        )
        recommendations.append(
            AdvisoryRecommendation(
                title="Reduce Outstanding Monthly EMI Burden",
                explanation=(
                    f"Your current debt obligations consume {current_foir:.1f}% of income, exceeding the {threshold:.1f}% benchmark."
                ),
                priority=priority,
                related_indicator="FOIR",
                suggested_action=(
                    "Focus surplus cash on prepaying high-interest personal loans or credit card balances, or explore loan tenure extension to lower monthly EMI burden."
                ),
            )
        )

    # Recommendation for Emergency Reserves
    if cov_months < Decimal("3.00"):
        priority = (
            RecommendationPriorityEnum.HIGH
            if cov_months < Decimal("1.00")
            else RecommendationPriorityEnum.MEDIUM
        )
        recommendations.append(
            AdvisoryRecommendation(
                title="Build a 3-to-6 Month Emergency Fund",
                explanation=(
                    f"Your liquid emergency reserves of ₹{savings:,.2f} cover only {cov_months:.1f} months of living costs."
                ),
                priority=priority,
                related_indicator="EMERGENCY_FUND",
                suggested_action=(
                    f"Set an immediate savings goal of ₹{(expenses * Decimal('3.00') - savings):,.2f} to establish a basic 3-month safety net in a liquid savings account or sweep-in fixed deposit."
                ),
            )
        )
    elif cov_months < Decimal("6.00"):
        recommendations.append(
            AdvisoryRecommendation(
                title="Bolster Emergency Reserves to 6 Months",
                explanation=f"You currently have {cov_months:.1f} months of expense buffer, which provides moderate resilience.",
                priority=RecommendationPriorityEnum.LOW,
                related_indicator="EMERGENCY_FUND",
                suggested_action="Gradually increase your emergency reserves toward 6 full months of expenses to safeguard against extended disruptions.",
            )
        )

    # Recommendation for Thin Disposable Income
    if ZERO <= disposable_inc and (income > ZERO and (disposable_inc / income) < Decimal("0.15")):
        recommendations.append(
            AdvisoryRecommendation(
                title="Enhance Monthly Disposable Buffer",
                explanation=(
                    f"Your disposable cash buffer is ₹{disposable_inc:,.2f} (under 15% of net income). Any unexpected rise in expenses could trigger a deficit."
                ),
                priority=RecommendationPriorityEnum.MEDIUM,
                related_indicator="DISPOSABLE_INCOME",
                suggested_action="Audit recurring subscriptions and discretionary expenses to create a minimum 15-20% monthly disposable margin.",
            )
        )

    # Positive Reinforcement if all indicators are healthy
    if not recommendations:
        recommendations.append(
            AdvisoryRecommendation(
                title="Maintain Disciplined Financial Position",
                explanation=(
                    f"Your debt obligations ({current_foir:.1f}% FOIR) are conservative, your emergency fund covers {cov_months:.1f} months, "
                    f"and you retain ₹{disposable_inc:,.2f} in disposable income."
                ),
                priority=RecommendationPriorityEnum.LOW,
                related_indicator="GENERAL",
                suggested_action="Continue regular savings habits and consider channeling surplus cash flow into disciplined long-term index investments or wealth creation goals.",
            )
        )

    # 6. Executive Summary Narrative
    if overall_category == RiskLevelEnum.LOW:
        summary = (
            f"Your financial risk score is {overall_score:.1f}/100 ({overall_category.value}). "
            f"You maintain a conservative debt ratio ({current_foir:.1f}%), healthy emergency reserve ({cov_months:.1f} months), "
            f"and consistent monthly cash flow buffer (₹{disposable_inc:,.2f})."
        )
    elif overall_category == RiskLevelEnum.MODERATE:
        summary = (
            f"Your financial risk score is {overall_score:.1f}/100 ({overall_category.value}). "
            f"Your debt obligations ({current_foir:.1f}%) and living expenses are manageable, "
            f"though emergency fund coverage ({cov_months:.1f} months) or disposable headroom warrant attention."
        )
    elif overall_category == RiskLevelEnum.HIGH:
        summary = (
            f"Your financial risk score is {overall_score:.1f}/100 ({overall_category.value}). "
            f"Your debt obligations ({current_foir:.1f}%) or limited emergency cushion ({cov_months:.1f} months) "
            "place elevated strain on your personal balance sheet."
        )
    else:
        summary = (
            f"Your financial risk score is {overall_score:.1f}/100 ({overall_category.value}). "
            "Critical indicators triggered: Elevated debt burden, cash flow deficit, or depleted emergency reserves. "
            "Immediate financial corrective action is advised."
        )

    return RiskAssessmentResponse(
        overall_risk_score=overall_score,
        overall_risk_category=overall_category,
        monthly_net_income=income,
        existing_monthly_emi=existing_emi,
        monthly_expenses=expenses,
        emergency_savings=savings,
        disposable_monthly_income=disposable_inc,
        foir_percentage=current_foir,
        current_foir_percentage=current_foir,
        configured_foir_threshold=threshold,
        emergency_fund_coverage_months=cov_months,
        indicators=indicators,
        triggered_warnings=warnings,
        recommendations=recommendations,
        summary_message=summary,
        assessment_disclaimer=DISCLAIMER_TEXT,
    )
