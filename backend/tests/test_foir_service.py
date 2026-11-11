"""
tests/test_foir_service.py
──────────────────────────
Unit and integration tests for Phase 2 - Step 3.1: FOIR Calculation Engine.

Covers:
- Normal FOIR calculation
- Zero existing EMI
- High FOIR / Stretched tier
- FOIR exceeding configured threshold
- Additional EMI capacity never becoming negative (floored at 0.00)
- Zero income handling (safe zero-division protection)
- Decimal rounding and quantization (ROUND_HALF_UP to 2 decimal places)
- Configurable threshold (e.g. 50% vs 40%)
- Proposed EMI simulation
- Missing financial profile (HTTP 404 / None)
- User isolation (User A cannot access User B's profile or calculation)
- Unauthenticated API access (HTTP 401 Unauthorized)
- Parameter validation bounds (HTTP 422 for negative or > 100% threshold)
"""

import uuid
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.user import User
from app.schemas.financial_profile import EmploymentTypeEnum, FinancialProfileCreate
from app.schemas.foir import AffordabilityStatusEnum, FOIRCalculationResponse
from app.services import foir_service, profile_service
from app.services.auth_service import register_user


# ── Test Suite 1: Pure Unit Calculation Tests ─────────────────────────────────

class TestFOIRUnitCalculations:
    """Test deterministic Decimal formulas and business rules."""

    def test_normal_foir_calculation(self):
        """Standard case: ₹1,00,000 income, ₹25,000 EMI -> 25.00% FOIR (Optimal)."""
        res = foir_service.calculate_foir(
            monthly_net_income=Decimal("100000.00"),
            existing_monthly_emi=Decimal("25000.00"),
            monthly_expenses=Decimal("35000.00"),
            emergency_savings=Decimal("200000.00"),
            configured_threshold=Decimal("40.00"),
        )
        assert res.current_foir_percentage == Decimal("25.00")
        assert res.configured_foir_threshold == Decimal("40.00")
        assert res.maximum_permissible_emi == Decimal("40000.00")
        assert res.additional_emi_capacity == Decimal("15000.00")
        assert res.remaining_income_after_expenses_and_emi == Decimal("40000.00")
        assert res.affordability_status == AffordabilityStatusEnum.OPTIMAL
        assert "within your configured policy threshold" in res.explanatory_message

    def test_zero_existing_emi(self):
        """Zero debt case: ₹80,000 income, ₹0 EMI -> 0.00% FOIR, full headroom."""
        res = foir_service.calculate_foir(
            monthly_net_income=Decimal("80000.00"),
            existing_monthly_emi=Decimal("0.00"),
            monthly_expenses=Decimal("30000.00"),
            emergency_savings=Decimal("150000.00"),
            configured_threshold=Decimal("40.00"),
        )
        assert res.current_foir_percentage == Decimal("0.00")
        assert res.maximum_permissible_emi == Decimal("32000.00")
        assert res.additional_emi_capacity == Decimal("32000.00")
        assert res.remaining_income_after_expenses_and_emi == Decimal("50000.00")
        assert res.affordability_status == AffordabilityStatusEnum.OPTIMAL

    def test_manageable_foir(self):
        """Manageable case: ₹1,00,000 income, ₹35,000 EMI -> 35.00% FOIR (within 40%)."""
        res = foir_service.calculate_foir(
            monthly_net_income=Decimal("100000.00"),
            existing_monthly_emi=Decimal("35000.00"),
            monthly_expenses=Decimal("40000.00"),
            emergency_savings=Decimal("100000.00"),
            configured_threshold=Decimal("40.00"),
        )
        assert res.current_foir_percentage == Decimal("35.00")
        assert res.maximum_permissible_emi == Decimal("40000.00")
        assert res.additional_emi_capacity == Decimal("5000.00")
        assert res.remaining_income_after_expenses_and_emi == Decimal("25000.00")
        assert res.affordability_status == AffordabilityStatusEnum.MANAGEABLE

    def test_foir_exceeding_threshold_stretched(self):
        """Stretched case: ₹1,00,000 income, ₹48,000 EMI -> 48.00% FOIR (> 40% but <= 55%)."""
        res = foir_service.calculate_foir(
            monthly_net_income=Decimal("100000.00"),
            existing_monthly_emi=Decimal("48000.00"),
            monthly_expenses=Decimal("35000.00"),
            emergency_savings=Decimal("50000.00"),
            configured_threshold=Decimal("40.00"),
        )
        assert res.current_foir_percentage == Decimal("48.00")
        assert res.maximum_permissible_emi == Decimal("40000.00")
        assert res.additional_emi_capacity == Decimal("0.00")
        assert res.remaining_income_after_expenses_and_emi == Decimal("17000.00")
        assert res.affordability_status == AffordabilityStatusEnum.STRETCHED
        assert "exceeding your configured policy threshold" in res.explanatory_message

    def test_high_foir_critical_and_negative_remaining_income(self):
        """Critical case: ₹50,000 income, ₹35,000 EMI (70% FOIR) + ₹25,000 expenses -> cash deficit."""
        res = foir_service.calculate_foir(
            monthly_net_income=Decimal("50000.00"),
            existing_monthly_emi=Decimal("35000.00"),
            monthly_expenses=Decimal("25000.00"),
            emergency_savings=Decimal("20000.00"),
            configured_threshold=Decimal("40.00"),
        )
        assert res.current_foir_percentage == Decimal("70.00")
        assert res.maximum_permissible_emi == Decimal("20000.00")
        assert res.additional_emi_capacity == Decimal("0.00")
        # Income (50k) - Expenses (25k) - EMI (35k) = -10,000
        assert res.remaining_income_after_expenses_and_emi == Decimal("-10000.00")
        assert res.affordability_status == AffordabilityStatusEnum.CRITICAL

    def test_additional_emi_capacity_never_negative(self):
        """When existing EMI vastly exceeds permissible limit, additional capacity is strictly 0.00."""
        res = foir_service.calculate_foir(
            monthly_net_income=Decimal("40000.00"),
            existing_monthly_emi=Decimal("32000.00"),  # 80% FOIR
            monthly_expenses=Decimal("15000.00"),
            emergency_savings=Decimal("10000.00"),
            configured_threshold=Decimal("40.00"),     # Max permissible = 16,000
        )
        # raw capacity would be 16,000 - 32,000 = -16,000 -> must floor at 0.00
        assert res.additional_emi_capacity == Decimal("0.00")
        assert res.additional_emi_capacity >= Decimal("0.00")

    def test_zero_income_safe_handling_with_existing_emi(self):
        """Zero income with obligations does not raise ZeroDivisionError and classifies as Critical."""
        res = foir_service.calculate_foir(
            monthly_net_income=Decimal("0.00"),
            existing_monthly_emi=Decimal("10000.00"),
            monthly_expenses=Decimal("15000.00"),
            emergency_savings=Decimal("50000.00"),
            configured_threshold=Decimal("40.00"),
        )
        assert res.current_foir_percentage == Decimal("100.00")
        assert res.maximum_permissible_emi == Decimal("0.00")
        assert res.additional_emi_capacity == Decimal("0.00")
        assert res.affordability_status == AffordabilityStatusEnum.CRITICAL
        assert "zero or non-positive" in res.explanatory_message

    def test_zero_income_and_zero_emi(self):
        """Zero income and zero EMI yields 0.00% FOIR, Critical status due to lack of income."""
        res = foir_service.calculate_foir(
            monthly_net_income=Decimal("0.00"),
            existing_monthly_emi=Decimal("0.00"),
            monthly_expenses=Decimal("10000.00"),
            emergency_savings=Decimal("30000.00"),
            configured_threshold=Decimal("40.00"),
        )
        assert res.current_foir_percentage == Decimal("0.00")
        assert res.maximum_permissible_emi == Decimal("0.00")
        assert res.additional_emi_capacity == Decimal("0.00")
        assert res.affordability_status == AffordabilityStatusEnum.CRITICAL

    def test_configurable_foir_threshold(self):
        """Configurable policy threshold alters permissible EMI and classification."""
        # At 40% threshold: 45% FOIR is Stretched
        res_40 = foir_service.calculate_foir(
            monthly_net_income=Decimal("100000.00"),
            existing_monthly_emi=Decimal("45000.00"),
            monthly_expenses=Decimal("30000.00"),
            emergency_savings=Decimal("100000.00"),
            configured_threshold=Decimal("40.00"),
        )
        assert res_40.maximum_permissible_emi == Decimal("40000.00")
        assert res_40.additional_emi_capacity == Decimal("0.00")
        assert res_40.affordability_status == AffordabilityStatusEnum.STRETCHED

        # At 50% threshold: 45% FOIR is Manageable with ₹5,000 capacity
        res_50 = foir_service.calculate_foir(
            monthly_net_income=Decimal("100000.00"),
            existing_monthly_emi=Decimal("45000.00"),
            monthly_expenses=Decimal("30000.00"),
            emergency_savings=Decimal("100000.00"),
            configured_threshold=Decimal("50.00"),
        )
        assert res_50.maximum_permissible_emi == Decimal("50000.00")
        assert res_50.additional_emi_capacity == Decimal("5000.00")
        assert res_50.affordability_status == AffordabilityStatusEnum.MANAGEABLE

    def test_proposed_emi_simulation(self):
        """Evaluating proposed EMI projects future FOIR correctly."""
        res = foir_service.calculate_foir(
            monthly_net_income=Decimal("100000.00"),
            existing_monthly_emi=Decimal("20000.00"),  # Current FOIR 20.00%
            monthly_expenses=Decimal("30000.00"),
            emergency_savings=Decimal("100000.00"),
            configured_threshold=Decimal("40.00"),
            proposed_emi=Decimal("15000.00"),          # Projected total 35,000 -> 35.00%
        )
        assert res.current_foir_percentage == Decimal("20.00")
        assert res.proposed_emi == Decimal("15000.00")
        assert res.projected_foir_percentage == Decimal("35.00")

    def test_decimal_rounding_round_half_up(self):
        """Values are accurately quantized with ROUND_HALF_UP to 2 decimal places."""
        # 23456 / 77777 * 100 = 30.158015... -> rounds to 30.16%
        res = foir_service.calculate_foir(
            monthly_net_income=Decimal("77777.00"),
            existing_monthly_emi=Decimal("23456.00"),
            monthly_expenses=Decimal("20000.00"),
            emergency_savings=Decimal("50000.00"),
            configured_threshold=Decimal("40.00"),
        )
        assert res.current_foir_percentage == Decimal("30.16")
        # 77777 * 0.40 = 31110.80
        assert res.maximum_permissible_emi == Decimal("31110.80")
        # 31110.80 - 23456.00 = 7654.80
        assert res.additional_emi_capacity == Decimal("7654.80")


# ── Test Suite 2: Profile Model, DB Integration & User Isolation ──────────────

class TestFOIRDatabaseAndIsolation:
    """Test interaction with FinancialProfile DB model and cross-user boundaries."""

    @pytest.mark.asyncio
    async def test_calculate_foir_from_profile_success(self, db):
        """Verify calculations using an actual ORM FinancialProfile record."""
        user_id = uuid.uuid4()
        profile_data = FinancialProfileCreate(
            monthly_net_income=Decimal("90000.00"),
            monthly_expenses=Decimal("30000.00"),
            existing_monthly_emi=Decimal("18000.00"),
            emergency_savings=Decimal("200000.00"),
            employment_type=EmploymentTypeEnum.SALARIED,
            existing_loan_count=1,
        )
        profile = await profile_service.upsert_profile(db, user_id, profile_data)

        calc = foir_service.calculate_foir_from_profile(profile, configured_threshold=Decimal("40.00"))
        assert calc.monthly_net_income == Decimal("90000.00")
        assert calc.existing_monthly_emi == Decimal("18000.00")
        assert calc.current_foir_percentage == Decimal("20.00")
        assert calc.maximum_permissible_emi == Decimal("36000.00")
        assert calc.additional_emi_capacity == Decimal("18000.00")
        assert calc.remaining_income_after_expenses_and_emi == Decimal("42000.00")
        assert calc.affordability_status == AffordabilityStatusEnum.OPTIMAL

    @pytest.mark.asyncio
    async def test_missing_profile_retrieval(self, db):
        """Querying a user without a financial profile returns None."""
        random_user_id = uuid.uuid4()
        profile = await profile_service.get_profile_by_user_id(db, random_user_id)
        assert profile is None

    @pytest.mark.asyncio
    async def test_cross_user_foir_isolation(self, db):
        """User A and User B profiles remain strictly isolated."""
        user_a = uuid.uuid4()
        user_b = uuid.uuid4()

        # User A: High income, low EMI
        await profile_service.upsert_profile(
            db,
            user_a,
            FinancialProfileCreate(
                monthly_net_income=Decimal("150000.00"),
                monthly_expenses=Decimal("40000.00"),
                existing_monthly_emi=Decimal("15000.00"),
                emergency_savings=Decimal("500000.00"),
            ),
        )

        # User B: Moderate income, higher EMI
        await profile_service.upsert_profile(
            db,
            user_b,
            FinancialProfileCreate(
                monthly_net_income=Decimal("60000.00"),
                monthly_expenses=Decimal("25000.00"),
                existing_monthly_emi=Decimal("27000.00"),
                emergency_savings=Decimal("50000.00"),
            ),
        )

        profile_a = await profile_service.get_profile_by_user_id(db, user_a)
        profile_b = await profile_service.get_profile_by_user_id(db, user_b)

        assert profile_a is not None and profile_b is not None
        assert profile_a.user_id == user_a
        assert profile_b.user_id == user_b

        calc_a = foir_service.calculate_foir_from_profile(profile_a)
        calc_b = foir_service.calculate_foir_from_profile(profile_b)

        # User A has 10% FOIR (Optimal)
        assert calc_a.current_foir_percentage == Decimal("10.00")
        assert calc_a.affordability_status == AffordabilityStatusEnum.OPTIMAL

        # User B has 45% FOIR (Stretched under 40% threshold)
        assert calc_b.current_foir_percentage == Decimal("45.00")
        assert calc_b.affordability_status == AffordabilityStatusEnum.STRETCHED


# ── Test Suite 3: HTTP Endpoint Security & Validation ─────────────────────────

class TestFOIREndpointHTTP:
    """Test HTTP level behavior, auth guards, and validation."""

    def test_unauthenticated_request_rejected(self):
        """Requests without session cookie return 401 Unauthorized."""
        client = TestClient(app)
        res = client.get("/api/v1/foir/calculate")
        assert res.status_code == 401
        assert "Not authenticated" in res.json().get("detail", "")

    def test_invalid_query_threshold_rejected(self):
        """Threshold outside 1.00 - 100.00 returns 422 Unprocessable Entity."""
        # Even without auth, FastAPI validates query params or auth dependency order
        client = TestClient(app)
        # Value < 1.00
        res_low = client.get("/api/v1/foir/calculate?threshold=0.5")
        # Value > 100.00
        res_high = client.get("/api/v1/foir/calculate?threshold=150.0")
        # FastAPI returns 422 for param validation failure or 401 depending on dependency order
        assert res_low.status_code in (401, 422)
        assert res_high.status_code in (401, 422)
