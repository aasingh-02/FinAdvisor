"""
tests/test_emi_service.py
─────────────────────────
Unit tests for deterministic EMI calculation service and amortization schedules.

Covers:
- Standard reducing-balance loan calculation
- Reference case: ₹10,00,000 at 9% p.a. for 60 months (EMI = ₹20,758.36)
- Zero-interest loan (0% APR)
- Very low interest rate (0.01% p.a.)
- Large principal (₹50 Crores)
- Short tenure (1 month)
- Invalid input validation (Pydantic schema bounds)
- Amortization schedule monotonic principal reduction
- Final closing balance reconciliation to exactly 0.00
- Total principal repaid equals original principal
- Total repayment equals principal plus total interest
"""

from decimal import Decimal
import pytest
from pydantic import ValidationError

from app.schemas.emi import EMICalculationRequest
from app.services import emi_service


class TestEMISchemas:
    """Input validation tests for EMI request schema."""

    def test_valid_request(self):
        req = EMICalculationRequest(
            principal_amount=Decimal("1000000.00"),
            annual_interest_rate=Decimal("9.00"),
            tenure_months=60,
        )
        assert req.principal_amount == Decimal("1000000.00")
        assert req.annual_interest_rate == Decimal("9.00")
        assert req.tenure_months == 60

    def test_zero_principal_rejected(self):
        with pytest.raises(ValidationError, match="greater than 0"):
            EMICalculationRequest(
                principal_amount=Decimal("0.00"),
                annual_interest_rate=Decimal("8.50"),
                tenure_months=12,
            )

    def test_negative_principal_rejected(self):
        with pytest.raises(ValidationError, match="greater than 0"):
            EMICalculationRequest(
                principal_amount=Decimal("-50000.00"),
                annual_interest_rate=Decimal("8.50"),
                tenure_months=12,
            )

    def test_negative_interest_rate_rejected(self):
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            EMICalculationRequest(
                principal_amount=Decimal("100000.00"),
                annual_interest_rate=Decimal("-1.50"),
                tenure_months=12,
            )

    def test_zero_tenure_rejected(self):
        with pytest.raises(ValidationError, match="greater than 0"):
            EMICalculationRequest(
                principal_amount=Decimal("100000.00"),
                annual_interest_rate=Decimal("8.50"),
                tenure_months=0,
            )

    def test_negative_tenure_rejected(self):
        with pytest.raises(ValidationError, match="greater than 0"):
            EMICalculationRequest(
                principal_amount=Decimal("100000.00"),
                annual_interest_rate=Decimal("8.50"),
                tenure_months=-6,
            )

    def test_excessive_principal_rejected(self):
        with pytest.raises(ValidationError, match="less than or equal to"):
            EMICalculationRequest(
                principal_amount=Decimal("2000000000.00"),  # 200 Crores exceeds 100 Crores limit
                annual_interest_rate=Decimal("8.50"),
                tenure_months=60,
            )

    def test_excessive_interest_rate_rejected(self):
        with pytest.raises(ValidationError, match="less than or equal to"):
            EMICalculationRequest(
                principal_amount=Decimal("100000.00"),
                annual_interest_rate=Decimal("105.00"),  # > 100%
                tenure_months=12,
            )

    def test_excessive_tenure_rejected(self):
        with pytest.raises(ValidationError, match="less than or equal to"):
            EMICalculationRequest(
                principal_amount=Decimal("100000.00"),
                annual_interest_rate=Decimal("8.50"),
                tenure_months=700,  # > 600 months (50 years)
            )


class TestEMICalculationService:
    """Core mathematical and amortization schedule service tests."""

    def test_reference_loan_calculation(self):
        """
        User reference case:
        Principal: ₹10,00,000, Annual Interest: 9%, Tenure: 60 months.
        Expected EMI is ₹20,758.36 (exact reducing-balance unrounded is 20,758.3552..., rounded to 20,758.36).
        """
        P = Decimal("1000000.00")
        rate = Decimal("9.00")
        tenure = 60

        result = emi_service.calculate_emi_with_schedule(P, rate, tenure)

        # Standard mathematical reducing-balance EMI check
        assert result.monthly_emi == Decimal("20758.36")
        assert len(result.amortization_schedule) == 60
        assert result.tenure_months == 60
        assert result.principal_amount == P

        # Reconcile full repayment and principal
        total_principal_repaid = sum(item.principal_component for item in result.amortization_schedule)
        assert total_principal_repaid == P

        total_repaid_schedule = sum(item.emi_amount for item in result.amortization_schedule)
        assert total_repaid_schedule == result.total_repayment
        assert result.total_repayment == P + result.total_interest

        # Final month balance is exactly 0.00
        assert result.amortization_schedule[-1].closing_balance == Decimal("0.00")

    def test_zero_interest_loan(self):
        """Zero-interest loan: Total interest is 0, EMI is exactly P / tenure."""
        P = Decimal("60000.00")
        rate = Decimal("0.00")
        tenure = 6

        result = emi_service.calculate_emi_with_schedule(P, rate, tenure)

        assert result.monthly_emi == Decimal("10000.00")
        assert result.total_interest == Decimal("0.00")
        assert result.total_repayment == Decimal("60000.00")
        assert result.principal_percentage == Decimal("100.00")
        assert result.interest_percentage == Decimal("0.00")

        # Every month interest component is 0.00
        for item in result.amortization_schedule:
            assert item.interest_component == Decimal("0.00")
            assert item.principal_component == Decimal("10000.00")

        assert result.amortization_schedule[-1].closing_balance == Decimal("0.00")

    def test_zero_interest_odd_rounding_reconciliation(self):
        """Zero-interest with odd division (e.g. ₹100 over 3 months -> 33.33, 33.33, 33.34)."""
        P = Decimal("100.00")
        rate = Decimal("0.00")
        tenure = 3

        result = emi_service.calculate_emi_with_schedule(P, rate, tenure)

        assert result.monthly_emi == Decimal("33.33")
        total_principal = sum(item.principal_component for item in result.amortization_schedule)
        assert total_principal == Decimal("100.00")
        assert result.amortization_schedule[-1].closing_balance == Decimal("0.00")
        assert result.amortization_schedule[-1].emi_amount == Decimal("33.34")

    def test_very_low_interest_rate(self):
        """Extremely low interest rate (0.01% p.a.)."""
        P = Decimal("100000.00")
        rate = Decimal("0.01")
        tenure = 12

        result = emi_service.calculate_emi_with_schedule(P, rate, tenure)

        assert result.monthly_emi > Decimal("8333.00")
        assert result.total_interest > Decimal("0.00")
        assert result.total_repayment > P
        assert result.amortization_schedule[-1].closing_balance == Decimal("0.00")

    def test_large_principal(self):
        """Large commercial loan of ₹50 Crores (500,000,000)."""
        P = Decimal("500000000.00")
        rate = Decimal("8.50")
        tenure = 120  # 10 years

        result = emi_service.calculate_emi_with_schedule(P, rate, tenure)

        assert result.monthly_emi > Decimal("6000000.00")
        assert result.amortization_schedule[-1].closing_balance == Decimal("0.00")
        total_principal = sum(item.principal_component for item in result.amortization_schedule)
        assert total_principal == P

    def test_one_month_tenure(self):
        """Single month tenure: entire principal plus one month interest repaid at once."""
        P = Decimal("50000.00")
        rate = Decimal("12.00")  # 12% annual = 1% per month = ₹500 interest
        tenure = 1

        result = emi_service.calculate_emi_with_schedule(P, rate, tenure)

        assert len(result.amortization_schedule) == 1
        item = result.amortization_schedule[0]
        assert item.month == 1
        assert item.opening_balance == Decimal("50000.00")
        assert item.interest_component == Decimal("500.00")
        assert item.principal_component == Decimal("50000.00")
        assert item.emi_amount == Decimal("50500.00")
        assert item.closing_balance == Decimal("0.00")
        assert result.total_interest == Decimal("500.00")
        assert result.total_repayment == Decimal("50500.00")

    def test_amortization_monotonic_balance_reduction(self):
        """Verify opening balance is strictly greater than closing balance each month."""
        P = Decimal("300000.00")
        rate = Decimal("10.50")
        tenure = 24

        result = emi_service.calculate_emi_with_schedule(P, rate, tenure)

        for item in result.amortization_schedule:
            assert item.opening_balance > item.closing_balance
            assert item.principal_component > Decimal("0.00")
            assert item.interest_component >= Decimal("0.00")
            assert item.opening_balance - item.principal_component == item.closing_balance

        # First month opening balance must equal original principal
        assert result.amortization_schedule[0].opening_balance == P
        # Last month closing balance must be exactly 0.00
        assert result.amortization_schedule[-1].closing_balance == Decimal("0.00")

    def test_percentages_sum_to_100(self):
        """Ensure visual breakdown percentages add up to 100.00%."""
        result = emi_service.calculate_emi_with_schedule(
            Decimal("500000.00"),
            Decimal("11.50"),
            36,
        )
        assert result.principal_percentage + result.interest_percentage == Decimal("100.00")
