"""
app/services/foir_service.py
────────────────────────────
Deterministic Fixed Obligation to Income Ratio (FOIR) calculation engine.

Guarantees:
- Uses Python Decimal with high precision (35 decimal places) for intermediate math.
- Currency and percentage values are quantized to 2 decimal places using ROUND_HALF_UP.
- Configurable policy threshold (default: 40.00%).
- Clearly distinguishes illustrative policy benchmark from commercial lender underwriting criteria.
- Additional EMI capacity is strictly non-negative: max(0, maximum_permissible_emi - existing_monthly_emi).
- Safely handles zero or non-positive net income without ZeroDivisionError.
- Does not modify database state (pure computation).
"""

from decimal import Decimal, ROUND_HALF_UP, getcontext
from typing import Optional

from app.models.financial_profile import FinancialProfile
from app.schemas.foir import AffordabilityStatusEnum, FOIRCalculationResponse

# Two decimal places rounding constant
CENT = Decimal("0.01")
ZERO = Decimal("0.00")
HUNDRED = Decimal("100.00")


def calculate_foir(
    monthly_net_income: Decimal,
    existing_monthly_emi: Decimal,
    monthly_expenses: Decimal,
    emergency_savings: Decimal,
    configured_threshold: Decimal = Decimal("40.00"),
    proposed_emi: Optional[Decimal] = None,
) -> FOIRCalculationResponse:
    """
    Compute FOIR and borrowing affordability metrics.

    Args:
        monthly_net_income: Net take-home monthly earnings (> 0 expected).
        existing_monthly_emi: Existing monthly loan/credit obligations (>= 0).
        monthly_expenses: Regular monthly household/living expenses (>= 0).
        emergency_savings: Total liquid savings reserve (>= 0).
        configured_threshold: Policy FOIR limit percentage (default 40.00%).
        proposed_emi: Optional additional monthly loan EMI to evaluate impact.

    Returns:
        FOIRCalculationResponse with deterministic calculations and risk classification.
    """
    # Enforce high internal precision for calculations
    getcontext().prec = 35

    income = monthly_net_income.quantize(CENT, rounding=ROUND_HALF_UP)
    existing_emi = existing_monthly_emi.quantize(CENT, rounding=ROUND_HALF_UP)
    expenses = monthly_expenses.quantize(CENT, rounding=ROUND_HALF_UP)
    savings = emergency_savings.quantize(CENT, rounding=ROUND_HALF_UP)
    threshold = configured_threshold.quantize(CENT, rounding=ROUND_HALF_UP)

    # 1. Current FOIR calculation with safe zero-income handling
    if income > ZERO:
        current_foir = ((existing_emi / income) * HUNDRED).quantize(CENT, rounding=ROUND_HALF_UP)
    else:
        # Zero or negative income: if there are existing EMIs, FOIR is at least 100%, else 0%
        current_foir = HUNDRED if existing_emi > ZERO else ZERO

    # 2. Maximum Permissible EMI under configured policy threshold
    if income > ZERO:
        max_permissible_emi = (income * (threshold / HUNDRED)).quantize(CENT, rounding=ROUND_HALF_UP)
    else:
        max_permissible_emi = ZERO

    # 3. Available Additional EMI Capacity: max(0, max_permissible - existing)
    raw_capacity = max_permissible_emi - existing_emi
    additional_capacity = max(ZERO, raw_capacity).quantize(CENT, rounding=ROUND_HALF_UP)

    # 4. Remaining Income after living expenses and existing EMIs
    remaining_income = (income - expenses - existing_emi).quantize(CENT, rounding=ROUND_HALF_UP)

    # 5. Affordability Status Tier Determination
    # Tier Guidelines:
    # - Optimal: FOIR <= min(30%, threshold)
    # - Manageable: min(30%, threshold) < FOIR <= threshold
    # - Stretched: threshold < FOIR <= 55%
    # - Critical: FOIR > 55% or non-positive income
    if income <= ZERO:
        affordability_status = AffordabilityStatusEnum.CRITICAL
    elif current_foir <= min(Decimal("30.00"), threshold):
        affordability_status = AffordabilityStatusEnum.OPTIMAL
    elif current_foir <= threshold:
        affordability_status = AffordabilityStatusEnum.MANAGEABLE
    elif current_foir <= Decimal("55.00"):
        affordability_status = AffordabilityStatusEnum.STRETCHED
    else:
        affordability_status = AffordabilityStatusEnum.CRITICAL

    # 6. Optional Proposed Loan Simulation
    quantized_proposed_emi: Optional[Decimal] = None
    projected_foir: Optional[Decimal] = None
    if proposed_emi is not None:
        p_emi = proposed_emi.quantize(CENT, rounding=ROUND_HALF_UP)
        quantized_proposed_emi = p_emi
        total_proposed_obligations = existing_emi + p_emi
        if income > ZERO:
            projected_foir = ((total_proposed_obligations / income) * HUNDRED).quantize(
                CENT, rounding=ROUND_HALF_UP
            )
        else:
            projected_foir = HUNDRED if total_proposed_obligations > ZERO else ZERO

    # 7. Contextual Explanatory Message
    if income <= ZERO:
        message = (
            "Monthly net income is reported as zero or non-positive. "
            "FOIR cannot be reliably assessed without positive cash inflow. "
            f"Note: The configured policy threshold of {threshold}% is an illustrative benchmark; "
            "commercial lenders evaluate verified income and credit history for loan eligibility."
        )
    elif current_foir <= threshold:
        message = (
            f"Your current FOIR is {current_foir}%, which is within your configured policy threshold of {threshold}%. "
            f"You have an estimated additional monthly EMI capacity of ₹{additional_capacity:,.2f}. "
            f"Net monthly disposable cash flow after expenses and EMIs is ₹{remaining_income:,.2f}. "
            f"Note: The configured policy threshold of {threshold}% is an illustrative benchmark; "
            "actual lender eligibility depends on credit score, employer category, and specific underwriting criteria."
        )
    else:
        message = (
            f"Your current FOIR is {current_foir}%, exceeding your configured policy threshold of {threshold}%. "
            "Existing EMI commitments exhaust your permissible limit under this policy, "
            "leaving ₹0.00 in additional EMI headroom. "
            f"Net monthly disposable cash flow is ₹{remaining_income:,.2f}. "
            f"Note: The configured policy threshold of {threshold}% is an illustrative benchmark; "
            "commercial lenders typically restrict new unsecured borrowing when fixed obligations exceed 40-50%."
        )

    return FOIRCalculationResponse(
        monthly_net_income=income,
        existing_monthly_emi=existing_emi,
        monthly_expenses=expenses,
        emergency_savings=savings,
        current_foir_percentage=current_foir,
        configured_foir_threshold=threshold,
        maximum_permissible_emi=max_permissible_emi,
        additional_emi_capacity=additional_capacity,
        remaining_income_after_expenses_and_emi=remaining_income,
        affordability_status=affordability_status,
        explanatory_message=message,
        proposed_emi=quantized_proposed_emi,
        projected_foir_percentage=projected_foir,
    )


def calculate_foir_from_profile(
    profile: FinancialProfile,
    configured_threshold: Decimal = Decimal("40.00"),
    proposed_emi: Optional[Decimal] = None,
) -> FOIRCalculationResponse:
    """
    Convenience adapter to calculate FOIR directly from an ORM FinancialProfile instance.
    """
    return calculate_foir(
        monthly_net_income=profile.monthly_net_income,
        existing_monthly_emi=profile.existing_monthly_emi,
        monthly_expenses=profile.monthly_expenses,
        emergency_savings=profile.emergency_savings,
        configured_threshold=configured_threshold,
        proposed_emi=proposed_emi,
    )
