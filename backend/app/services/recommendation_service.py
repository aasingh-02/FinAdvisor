"""
app/services/recommendation_service.py
──────────────────────────────────────
Deterministic Personalized Loan Recommendation Engine.

Guarantees:
- Pure deterministic Python and Decimal arithmetic (ROUND_HALF_UP).
- Evaluates borrower affordability combining FOIR and actual disposable cash flow.
- Never recommends loans exceeding calculated prudent affordability limits.
- Supports 4 major loan categories: Personal, Home, Vehicle, Education.
- Adjusts safety margins for employment volatility and emergency reserve depth.
- Reuses the existing reducing-balance EMI engine (emi_service) and FOIR service.
- Returns structured no-recommendation responses when affordability is constrained.
- Includes mandatory transparency disclaimers (no loan approval guarantees).
"""

from decimal import Decimal, ROUND_HALF_UP, getcontext
from typing import Dict, List, Optional, Tuple

from app.models.financial_profile import FinancialProfile
from app.schemas.financial_profile import EmploymentTypeEnum
from app.schemas.recommendation import (
    FinancialEligibilitySnapshot,
    LoanCategoryEnum,
    LoanRecommendationItem,
    RecommendationRequest,
    RecommendationResponse,
    RiskConsiderations,
)
from app.services import emi_service, foir_service, risk_service

CENT = Decimal("0.01")
ZERO = Decimal("0.00")
HUNDRED = Decimal("100.00")

# Standard illustrative interest rates and tenure benchmarks for Indian financial institutions
CATEGORY_SPECS = {
    LoanCategoryEnum.PERSONAL_LOAN: {
        "display_name": "Personal Loan (Unsecured)",
        "assumed_rate": Decimal("13.50"),
        "default_tenure": 36,
        "min_tenure": 12,
        "max_tenure": 60,
        "description": "Short-to-medium term financing for immediate liquidity or debt consolidation.",
    },
    LoanCategoryEnum.HOME_LOAN: {
        "display_name": "Home Loan (Secured Property)",
        "assumed_rate": Decimal("8.50"),
        "default_tenure": 240,
        "min_tenure": 60,
        "max_tenure": 360,
        "description": "Long-term mortgage financing for residential purchase or construction.",
    },
    LoanCategoryEnum.VEHICLE_LOAN: {
        "display_name": "Auto / Vehicle Loan (Hypothecated)",
        "assumed_rate": Decimal("9.50"),
        "default_tenure": 60,
        "min_tenure": 24,
        "max_tenure": 84,
        "description": "Medium-term asset financing for new four-wheeler or commercial vehicle.",
    },
    LoanCategoryEnum.EDUCATION_LOAN: {
        "display_name": "Education Loan (Higher Studies)",
        "assumed_rate": Decimal("10.00"),
        "default_tenure": 84,
        "min_tenure": 36,
        "max_tenure": 120,
        "description": "Structured financing for higher academic degrees with extended repayment.",
    },
}

DISCLAIMER_TEXT = (
    "All loan recommendations, borrowing capacities, and interest rates presented are illustrative assumptions "
    "for personal financial planning purposes only. They do not constitute a formal loan offer, pre-approval, "
    "or guarantee of credit from any bank or financial institution. Actual loan terms, applicable interest rates, "
    "and sanction amounts depend strictly on lender underwriting criteria, CIBIL/credit score, and verified documentation."
)


def calculate_principal_from_emi(
    target_emi: Decimal,
    annual_interest_rate: Decimal,
    tenure_months: int,
) -> Decimal:
    """
    Derive the maximum loan principal supported by a target monthly installment.
    Formula:
        If r == 0: P = EMI * n
        If r > 0:  P = EMI * ((1 + r)^n - 1) / (r * (1 + r)^n)
    where r = annual_interest_rate / 1200.
    """
    getcontext().prec = 35

    if target_emi <= ZERO or tenure_months <= 0:
        return ZERO

    r = annual_interest_rate / Decimal("1200")
    n = tenure_months

    if r == ZERO:
        exact_principal = target_emi * Decimal(str(n))
    else:
        pow_factor = (Decimal("1") + r) ** n
        exact_principal = target_emi * (pow_factor - Decimal("1")) / (r * pow_factor)

    # Quantize and round down to nearest sensible denomination (multiple of 5,000 INR)
    if exact_principal <= Decimal("10000.00"):
        return exact_principal.quantize(CENT, rounding=ROUND_HALF_UP)

    denom = Decimal("5000.00")
    rounded = (exact_principal // denom) * denom
    return rounded.quantize(CENT, rounding=ROUND_HALF_UP)


def generate_loan_recommendations(
    profile: FinancialProfile,
    request_params: Optional[RecommendationRequest] = None,
) -> RecommendationResponse:
    """
    Execute deterministic affordability evaluation and generate tailored loan recommendations.
    """
    getcontext().prec = 35

    params = request_params or RecommendationRequest()
    threshold = params.foir_threshold or Decimal("40.00")

    income = profile.monthly_net_income.quantize(CENT, rounding=ROUND_HALF_UP)
    existing_emi = profile.existing_monthly_emi.quantize(CENT, rounding=ROUND_HALF_UP)
    expenses = profile.monthly_expenses.quantize(CENT, rounding=ROUND_HALF_UP)
    savings = profile.emergency_savings.quantize(CENT, rounding=ROUND_HALF_UP)

    # 1. Assess existing risk and FOIR metrics
    risk_res = risk_service.assess_profile_risk(profile, configured_threshold=threshold)
    foir_res = foir_service.calculate_foir_from_profile(profile, configured_threshold=threshold)

    current_foir = foir_res.current_foir_percentage
    disposable_income = (income - expenses - existing_emi).quantize(CENT, rounding=ROUND_HALF_UP)
    theoretical_capacity = foir_res.additional_emi_capacity
    coverage_months = risk_res.emergency_fund_coverage_months

    # 2. Safety Margins and Buffer Determination
    reasons_and_warnings: List[str] = []
    buffer_multiplier = Decimal("0.80")  # Default: reserve 20% of disposable cash flow for life contingencies

    # Employment Volatility Adjustment
    employment_type_str = str(profile.employment_type)
    if profile.employment_type in (EmploymentTypeEnum.SELF_EMPLOYED, EmploymentTypeEnum.BUSINESS):
        buffer_multiplier = Decimal("0.70")
        reasons_and_warnings.append(
            f"Self-employed / Business profile: A conservative 30% cash flow reserve buffer was applied to account for business income volatility."
        )

    # Emergency Reserve Depth Adjustment
    has_sufficient_emergency = coverage_months >= Decimal("3.00")
    if not has_sufficient_emergency:
        buffer_multiplier = min(buffer_multiplier, Decimal("0.60"))
        reasons_and_warnings.append(
            f"Emergency savings cover only {coverage_months:.1f} months of expenses (< 3 months). "
            "A conservative cash flow buffer was applied so you can simultaneously build emergency liquidity."
        )

    # Prudent Maximum Monthly EMI: bounded by both FOIR headroom and disposable cash flow
    prudent_from_cashflow = max(ZERO, disposable_income * buffer_multiplier).quantize(CENT, rounding=ROUND_HALF_UP)
    prudent_max_emi = min(theoretical_capacity, prudent_from_cashflow).quantize(CENT, rounding=ROUND_HALF_UP)

    # Compile Snapshots
    financial_snapshot = FinancialEligibilitySnapshot(
        monthly_net_income=income,
        existing_monthly_emi=existing_emi,
        monthly_expenses=expenses,
        emergency_savings=savings,
        current_foir_percentage=current_foir,
        configured_foir_threshold=threshold,
        disposable_monthly_income=disposable_income,
        theoretical_additional_capacity=theoretical_capacity,
        prudent_max_monthly_emi=prudent_max_emi,
        employment_type=employment_type_str,
    )

    risk_considerations = RiskConsiderations(
        overall_risk_category=risk_res.overall_risk_category.value,
        overall_risk_score=risk_res.overall_risk_score,
        emergency_fund_coverage_months=coverage_months,
        has_sufficient_emergency_fund=has_sufficient_emergency,
        has_cash_deficit=disposable_income < ZERO,
    )

    # 3. Eligibility Verification Guards
    is_eligible = True
    eligibility_summary = ""

    if income <= ZERO:
        is_eligible = False
        eligibility_summary = "Monthly net income is reported as zero or non-positive. Borrowing capacity cannot be established without verified positive earnings."
        reasons_and_warnings.append("No positive income flow reported to service debt.")
    elif disposable_income <= ZERO:
        is_eligible = False
        eligibility_summary = (
            f"Monthly cash flow deficit of ₹{abs(disposable_income):,.2f} detected. "
            "Existing loan EMIs and essential living costs fully exhaust your net monthly income."
        )
        reasons_and_warnings.append(
            f"Current expenses (₹{expenses:,.2f}) and existing EMIs (₹{existing_emi:,.2f}) exceed income (₹{income:,.2f}). Additional borrowing is unsafe."
        )
    elif current_foir >= threshold:
        is_eligible = False
        eligibility_summary = (
            f"Current fixed debt obligations consume {current_foir:.1f}% of net income, "
            f"reaching or exceeding your configured policy benchmark of {threshold:.1f}%."
        )
        reasons_and_warnings.append(
            f"Zero additional EMI capacity remaining under the {threshold:.1f}% FOIR benchmark."
        )
    elif prudent_max_emi < Decimal("1000.00"):
        is_eligible = False
        eligibility_summary = (
            "Available monthly debt servicing headroom after safety buffers is under ₹1,000. "
            "Borrowing capacity is insufficient for a viable commercial loan installment without impacting essential living expenses."
        )
        reasons_and_warnings.append("Prudent monthly repayment capacity is below standard minimum installment thresholds (₹1,000).")

    # If ineligible, return immediately with zero recommendations and clear warnings
    if not is_eligible:
        return RecommendationResponse(
            is_eligible=False,
            eligibility_summary=eligibility_summary,
            financial_snapshot=financial_snapshot,
            risk_considerations=risk_considerations,
            recommendations=[],
            reasons_and_warnings=reasons_and_warnings,
            assumptions_and_disclaimers=DISCLAIMER_TEXT,
        )

    # 4. Generate Personalized Recommendations for Eligible Profiles
    eligibility_summary = (
        f"You are eligible for additional borrowing with an estimated prudent monthly EMI capacity of ₹{prudent_max_emi:,.2f} "
        f"(within your {threshold:.1f}% FOIR policy benchmark and maintaining a {int((Decimal('1.00') - buffer_multiplier) * 100)}% disposable cash buffer)."
    )

    categories_to_evaluate: List[LoanCategoryEnum] = []
    if params.preferred_loan_category:
        categories_to_evaluate = [params.preferred_loan_category]
        # Include remaining categories as comparative scenarios
        for cat in LoanCategoryEnum:
            if cat not in categories_to_evaluate:
                categories_to_evaluate.append(cat)
    else:
        categories_to_evaluate = list(LoanCategoryEnum)

    recommendations: List[LoanRecommendationItem] = []

    for cat in categories_to_evaluate:
        specs = CATEGORY_SPECS[cat]
        assumed_rate = specs["assumed_rate"]
        tenure = specs["default_tenure"]

        # Respect user preferred tenure if provided for their primary category
        if cat == params.preferred_loan_category and params.preferred_tenure_months:
            tenure = max(specs["min_tenure"], min(specs["max_tenure"], params.preferred_tenure_months))

        # Determine Suggested Principal
        suitability_reason = ""
        is_user_custom_request = cat == params.preferred_loan_category and params.desired_loan_amount is not None

        if is_user_custom_request:
            desired_amt = params.desired_loan_amount.quantize(CENT, rounding=ROUND_HALF_UP)
            # Calculate what EMI the requested amount would require
            calc_req = emi_service.calculate_emi_with_schedule(desired_amt, assumed_rate, tenure)
            req_emi = calc_req.monthly_emi

            if req_emi <= prudent_max_emi:
                # Requested loan fits comfortably
                suggested_principal = desired_amt
                suitability_reason = (
                    f"Your requested loan of ₹{desired_amt:,.2f} requires an EMI of ₹{req_emi:,.2f}/month, "
                    f"which fits comfortably within your prudent capacity of ₹{prudent_max_emi:,.2f}."
                )
            else:
                # Requested loan exceeds prudent capacity -> suggest maximum affordable principal
                suggested_principal = calculate_principal_from_emi(prudent_max_emi, assumed_rate, tenure)
                reasons_and_warnings.append(
                    f"{specs['display_name']}: Requested loan of ₹{desired_amt:,.2f} requires an EMI of ₹{req_emi:,.2f}, "
                    f"exceeding your prudent monthly headroom of ₹{prudent_max_emi:,.2f}. "
                    f"Principal adjusted to the maximum affordable amount of ₹{suggested_principal:,.2f}."
                )
                suitability_reason = (
                    f"Adjusted to your maximum prudent capacity: An installment of ₹{prudent_max_emi:,.2f}/month "
                    f"supports a loan principal of ₹{suggested_principal:,.2f} over {tenure} months."
                )
        else:
            # Automatic sizing based on prudent max EMI
            suggested_principal = calculate_principal_from_emi(prudent_max_emi, assumed_rate, tenure)
            suitability_reason = (
                f"{specs['description']} Based on your ₹{prudent_max_emi:,.2f} monthly headroom, "
                f"you can comfortably service up to ₹{suggested_principal:,.2f} at an assumed rate of {assumed_rate:.2f}% p.a."
            )

        # Do not suggest micro-loans (< ₹10,000) for standard categories
        if suggested_principal < Decimal("10000.00"):
            continue

        # Execute standard reducing-balance math for exact precision and amortization
        emi_calc = emi_service.calculate_emi_with_schedule(
            principal_amount=suggested_principal,
            annual_interest_rate=assumed_rate,
            tenure_months=tenure,
        )

        projected_total_emi = existing_emi + emi_calc.monthly_emi
        projected_foir = ((projected_total_emi / income) * HUNDRED).quantize(CENT, rounding=ROUND_HALF_UP)

        # Affordability tier classification
        if projected_foir <= Decimal("30.00"):
            affordability_tier = "Optimal"
        elif projected_foir <= threshold:
            affordability_tier = "Manageable"
        else:
            affordability_tier = "Stretched"

        recommendations.append(
            LoanRecommendationItem(
                loan_category=cat,
                category_display_name=specs["display_name"],
                recommended_principal=suggested_principal,
                assumed_annual_interest_rate=assumed_rate,
                suggested_tenure_months=tenure,
                estimated_monthly_emi=emi_calc.monthly_emi,
                total_interest_payable=emi_calc.total_interest,
                total_repayment=emi_calc.total_repayment,
                projected_foir_percentage=projected_foir,
                affordability_classification=affordability_tier,
                suitability_reason=suitability_reason,
            )
        )

    return RecommendationResponse(
        is_eligible=len(recommendations) > 0,
        eligibility_summary=eligibility_summary,
        financial_snapshot=financial_snapshot,
        risk_considerations=risk_considerations,
        recommendations=recommendations,
        reasons_and_warnings=reasons_and_warnings,
        assumptions_and_disclaimers=DISCLAIMER_TEXT,
    )
