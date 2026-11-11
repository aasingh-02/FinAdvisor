"""
app/services/emi_service.py
───────────────────────────
Deterministic reducing-balance Equated Monthly Installment (EMI) calculation engine.

Guarantees:
- Uses Python Decimal with high intermediate precision (35 decimal places)
- Currency values quantized to 2 decimal places using ROUND_HALF_UP
- Supports zero-interest loans (0% APR)
- Generates month-by-month amortization schedule
- Reconciles rounding differences in the final installment so remaining balance is exactly 0.00
- Pure deterministic Python math (never uses AI or floating point)
"""

from decimal import Decimal, ROUND_HALF_UP, getcontext
from typing import List, Tuple

from app.schemas.emi import AmortizationScheduleItem, EMICalculationResponse

# Two decimal places rounding specifier
CENT = Decimal("0.01")


def calculate_emi_with_schedule(
    principal_amount: Decimal,
    annual_interest_rate: Decimal,
    tenure_months: int,
) -> EMICalculationResponse:
    """
    Compute reducing-balance EMI and complete monthly amortization schedule.

    Args:
        principal_amount: Principal loan amount (> 0)
        annual_interest_rate: Annual interest rate in percent (>= 0)
        tenure_months: Total loan tenure in months (> 0)

    Returns:
        EMICalculationResponse containing monthly EMI, total interest,
        total repayment, percentage breakdown, and full amortization schedule.
    """
    # Enforce high internal precision for intermediate calculations
    getcontext().prec = 35

    P = principal_amount.quantize(CENT, rounding=ROUND_HALF_UP)
    n = tenure_months
    annual_rate = annual_interest_rate

    # Monthly interest rate = Annual Rate / 12 / 100
    r = annual_rate / Decimal("1200")

    if r == Decimal("0"):
        # Zero-interest loan calculation
        standard_emi = (P / Decimal(str(n))).quantize(CENT, rounding=ROUND_HALF_UP)
    else:
        # Standard reducing-balance formula: EMI = P * r * (1 + r)^n / ((1 + r)^n - 1)
        pow_factor = (Decimal("1") + r) ** n
        exact_emi = P * r * pow_factor / (pow_factor - Decimal("1"))
        standard_emi = exact_emi.quantize(CENT, rounding=ROUND_HALF_UP)

    schedule: List[AmortizationScheduleItem] = []
    balance = P
    total_interest = Decimal("0.00")
    total_repayment = Decimal("0.00")

    for month in range(1, n + 1):
        opening_balance = balance

        if r == Decimal("0"):
            interest_component = Decimal("0.00")
        else:
            interest_component = (opening_balance * r).quantize(CENT, rounding=ROUND_HALF_UP)

        if month == n:
            # Final month reconciliation: pay exact remaining balance to reach 0.00
            principal_component = opening_balance
            installment_amount = (principal_component + interest_component).quantize(CENT, rounding=ROUND_HALF_UP)
            closing_balance = Decimal("0.00")
        else:
            principal_component = (standard_emi - interest_component).quantize(CENT, rounding=ROUND_HALF_UP)

            # Guard against edge-case where principal component exceeds balance
            if principal_component > opening_balance:
                principal_component = opening_balance
                installment_amount = principal_component + interest_component
                closing_balance = Decimal("0.00")
            else:
                installment_amount = standard_emi
                closing_balance = (opening_balance - principal_component).quantize(CENT, rounding=ROUND_HALF_UP)

        schedule.append(
            AmortizationScheduleItem(
                month=month,
                opening_balance=opening_balance,
                emi_amount=installment_amount,
                principal_component=principal_component,
                interest_component=interest_component,
                closing_balance=closing_balance,
            )
        )

        total_interest += interest_component
        total_repayment += installment_amount
        balance = closing_balance

    # Calculate percentage breakdown
    if total_repayment > Decimal("0.00"):
        principal_percentage = ((P / total_repayment) * Decimal("100.00")).quantize(CENT, rounding=ROUND_HALF_UP)
        interest_percentage = (Decimal("100.00") - principal_percentage).quantize(CENT, rounding=ROUND_HALF_UP)
    else:
        principal_percentage = Decimal("100.00")
        interest_percentage = Decimal("0.00")

    return EMICalculationResponse(
        principal_amount=P,
        annual_interest_rate=annual_rate.quantize(CENT, rounding=ROUND_HALF_UP),
        tenure_months=n,
        monthly_emi=standard_emi,
        total_interest=total_interest.quantize(CENT, rounding=ROUND_HALF_UP),
        total_repayment=total_repayment.quantize(CENT, rounding=ROUND_HALF_UP),
        principal_percentage=principal_percentage,
        interest_percentage=interest_percentage,
        amortization_schedule=schedule,
    )
