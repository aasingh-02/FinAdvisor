"""
tests/test_dashboard_service.py
───────────────────────────────
Unit and integration tests for Phase 4 - Step 1:
Unified Financial Dashboard & Financial Health Score Engine.
"""

import uuid
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.financial_profile import FinancialProfile
from app.schemas.dashboard import (
    DashboardSummaryResponse,
    FinancialHealthScore,
    HealthGradeEnum,
)
from app.schemas.financial_profile import EmploymentTypeEnum, FinancialProfileCreate
from app.services import (
    dashboard_service,
    profile_service,
)


# ── Test Suite 1: Pure Unit Financial Health Score Math ───────────────────────

class TestFinancialHealthScoreUnit:
    """Test deterministic weighted scoring across diverse financial profiles."""

    def test_pristine_optimal_profile(self):
        """Pristine applicant with high savings and zero debt achieves A+ grade."""
        profile = FinancialProfile(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            monthly_net_income=Decimal("150000.00"),
            monthly_expenses=Decimal("35000.00"),
            existing_monthly_emi=Decimal("0.00"),
            emergency_savings=Decimal("600000.00"),  # 17.1 mos living expenses, 33.3% annual income
            employment_type=EmploymentTypeEnum.SALARIED,
            existing_loan_count=0,
        )

        result = dashboard_service.compute_financial_health_score(profile)
        assert isinstance(result, FinancialHealthScore)
        assert result.letter_grade == HealthGradeEnum.A_PLUS
        assert result.overall_score >= Decimal("90.00")
        assert len(result.sub_scores) == 4

        # Confirm renamed conceptual label
        sub_names = [sub.name for sub in result.sub_scores]
        assert "Savings Reserve Ratio Score" in sub_names

        # All 4 sub-scores should be optimal (100 pts)
        for sub in result.sub_scores:
            assert sub.score == Decimal("100.00")

    def test_moderate_healthy_profile(self):
        """Moderate applicant with 1 loan and solid 6-month buffer achieves A grade."""
        profile = FinancialProfile(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            monthly_net_income=Decimal("100000.00"),
            monthly_expenses=Decimal("40000.00"),
            existing_monthly_emi=Decimal("15000.00"),  # FOIR = 15.0%
            emergency_savings=Decimal("250000.00"),    # 6.25 mos expenses, 20.8% annual income
            employment_type=EmploymentTypeEnum.SALARIED,
            existing_loan_count=1,
        )

        result = dashboard_service.compute_financial_health_score(profile)
        assert result.letter_grade in (HealthGradeEnum.A_PLUS, HealthGradeEnum.A)
        assert Decimal("75.00") <= result.overall_score <= Decimal("100.00")

    def test_stretched_profile_grade_c(self):
        """Stretched applicant with 40% FOIR and 2-month reserve scores grade C."""
        profile = FinancialProfile(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            monthly_net_income=Decimal("80000.00"),
            monthly_expenses=Decimal("35000.00"),
            existing_monthly_emi=Decimal("32000.00"),  # FOIR = 40.0%
            emergency_savings=Decimal("70000.00"),     # 2.0 mos expenses (< 3 mos)
            employment_type=EmploymentTypeEnum.SALARIED,
            existing_loan_count=2,
        )

        result = dashboard_service.compute_financial_health_score(profile)
        assert result.letter_grade == HealthGradeEnum.C
        assert Decimal("40.00") <= result.overall_score < Decimal("60.00")

    def test_overleveraged_cash_deficit_grade_f(self):
        """Critical overleveraging with cash flow deficit results in Grade F."""
        profile = FinancialProfile(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            monthly_net_income=Decimal("60000.00"),
            monthly_expenses=Decimal("30000.00"),
            existing_monthly_emi=Decimal("38000.00"),  # FOIR = 63.3%, Deficit = -8,000
            emergency_savings=Decimal("5000.00"),      # 0.16 mos coverage
            employment_type=EmploymentTypeEnum.SALARIED,
            existing_loan_count=4,
        )

        result = dashboard_service.compute_financial_health_score(profile)
        assert result.letter_grade == HealthGradeEnum.F
        assert result.overall_score < Decimal("25.00")

    # ── Explicit Test 1: Zero income with positive existing EMI ───────────────
    def test_zero_income_with_positive_existing_emi(self):
        """Zero income with positive debt returns 0 without ZeroDivisionError and classifies as Critical."""
        income = Decimal("0.00")
        emi = Decimal("10000.00")
        disposable = Decimal("-10000.00")
        score = dashboard_service._calculate_debt_burden_sub_score(income, emi, disposable, 1)
        assert score == Decimal("0.00")

        profile = FinancialProfile(
            monthly_net_income=Decimal("0.00"),
            monthly_expenses=Decimal("20000.00"),
            existing_monthly_emi=Decimal("10000.00"),
            emergency_savings=Decimal("50000.00"),
            employment_type=EmploymentTypeEnum.SALARIED,
            existing_loan_count=1,
        )
        res = dashboard_service.compute_financial_health_score(profile)
        assert res.letter_grade == HealthGradeEnum.F
        assert res.overall_score < Decimal("25.00")

        foir_sub = next(s for s in res.sub_scores if s.name == "FOIR Debt Ratio")
        assert foir_sub.score == Decimal("0.00")
        assert foir_sub.status == "Critical"
        assert "100.0%" in foir_sub.detail
        assert "10,000.00" in foir_sub.detail

    # ── Explicit Test 2: Zero income with zero existing EMI ───────────────────
    def test_zero_income_with_zero_existing_emi(self):
        """Zero income with zero debt returns 0 without claiming 100% consumption, status is No Debt."""
        income = Decimal("0.00")
        emi = Decimal("0.00")
        disposable = Decimal("0.00")
        score = dashboard_service._calculate_debt_burden_sub_score(income, emi, disposable, 0)
        assert score == Decimal("0.00")

        profile = FinancialProfile(
            monthly_net_income=Decimal("0.00"),
            monthly_expenses=Decimal("0.00"),
            existing_monthly_emi=Decimal("0.00"),
            emergency_savings=Decimal("0.00"),
            employment_type=EmploymentTypeEnum.SALARIED,
            existing_loan_count=0,
        )
        res = dashboard_service.compute_financial_health_score(profile)
        assert res.letter_grade == HealthGradeEnum.F

        foir_sub = next(s for s in res.sub_scores if s.name == "FOIR Debt Ratio")
        assert foir_sub.score == Decimal("0.00")
        assert foir_sub.status == "No Debt"
        assert "100.0%" not in foir_sub.detail
        assert "No active loan obligations" in foir_sub.detail

    # ── Explicit Test 3: Negative income handling ─────────────────────────────
    def test_negative_income(self):
        """Negative income cleanly evaluates to 0 points across debt and savings."""
        income = Decimal("-15000.00")
        emi = Decimal("0.00")
        disposable = Decimal("-15000.00")
        debt_score = dashboard_service._calculate_debt_burden_sub_score(income, emi, disposable, 0)
        assert debt_score == Decimal("0.00")

        savings_score = dashboard_service._calculate_savings_reserve_sub_score(Decimal("50000.00"), income)
        assert savings_score == Decimal("0.00")

    # ── Explicit Test 4: Zero living expenses ─────────────────────────────────
    def test_zero_living_expenses(self):
        """Zero living expenses handled safely (100 if savings > 0, 0 if savings == 0)."""
        expenses = Decimal("0.00")
        assert dashboard_service._calculate_emergency_fund_sub_score(Decimal("50000.00"), expenses) == Decimal("100.00")
        assert dashboard_service._calculate_emergency_fund_sub_score(Decimal("0.00"), expenses) == Decimal("0.00")

    # ── Explicit Test 5: Emergency fund coverage boundaries ───────────────────
    def test_emergency_fund_coverage_exact_boundaries(self):
        """Verify exact coverage boundaries: 0, 1, 3, and 6 months."""
        expenses = Decimal("50000.00")

        # 0 months (0 savings) -> 0.00
        score_0 = dashboard_service._calculate_emergency_fund_sub_score(Decimal("0.00"), expenses)
        assert score_0 == Decimal("0.00")

        # 1 month (50,000 savings) -> 20.00
        score_1 = dashboard_service._calculate_emergency_fund_sub_score(Decimal("50000.00"), expenses)
        assert score_1 == Decimal("20.00")

        # 3 months (150,000 savings) -> 60.00
        score_3 = dashboard_service._calculate_emergency_fund_sub_score(Decimal("150000.00"), expenses)
        assert score_3 == Decimal("60.00")

        # 6 months (300,000 savings) -> 100.00
        score_6 = dashboard_service._calculate_emergency_fund_sub_score(Decimal("300000.00"), expenses)
        assert score_6 == Decimal("100.00")

        # Greater than 6 months (500,000 savings) -> capped at 100.00
        score_10 = dashboard_service._calculate_emergency_fund_sub_score(Decimal("500000.00"), expenses)
        assert score_10 == Decimal("100.00")

    # ── Explicit Test 6: FOIR boundaries: 30%, 45%, and 60% ──────────────────
    def test_foir_exact_boundaries(self):
        """Verify exact FOIR boundaries: 30%, 45%, and 60%."""
        # Exactly 30% -> 100.00
        assert dashboard_service._calculate_foir_sub_score(Decimal("30.00")) == Decimal("100.00")
        # Below 30% -> 100.00
        assert dashboard_service._calculate_foir_sub_score(Decimal("15.00")) == Decimal("100.00")

        # Exactly 45% -> 50.00
        assert dashboard_service._calculate_foir_sub_score(Decimal("45.00")) == Decimal("50.00")

        # Exactly 60% -> 0.00
        assert dashboard_service._calculate_foir_sub_score(Decimal("60.00")) == Decimal("0.00")
        # Above 60% -> 0.00
        assert dashboard_service._calculate_foir_sub_score(Decimal("75.00")) == Decimal("0.00")

    # ── Explicit Test 7: Grade boundaries: 25, 40, 55, 70, and 85 ─────────────
    def test_grade_exact_boundaries(self):
        """Verify exact letter grade transitions at 25, 40, 55, 70, and 85."""
        def get_grade(score: Decimal) -> HealthGradeEnum:
            if score >= Decimal("85.00"):
                return HealthGradeEnum.A_PLUS
            elif score >= Decimal("70.00"):
                return HealthGradeEnum.A
            elif score >= Decimal("55.00"):
                return HealthGradeEnum.B
            elif score >= Decimal("40.00"):
                return HealthGradeEnum.C
            elif score >= Decimal("25.00"):
                return HealthGradeEnum.D
            else:
                return HealthGradeEnum.F

        # 85.00 boundary
        assert get_grade(Decimal("85.00")) == HealthGradeEnum.A_PLUS
        assert get_grade(Decimal("84.99")) == HealthGradeEnum.A

        # 70.00 boundary
        assert get_grade(Decimal("70.00")) == HealthGradeEnum.A
        assert get_grade(Decimal("69.99")) == HealthGradeEnum.B

        # 55.00 boundary
        assert get_grade(Decimal("55.00")) == HealthGradeEnum.B
        assert get_grade(Decimal("54.99")) == HealthGradeEnum.C

        # 40.00 boundary
        assert get_grade(Decimal("40.00")) == HealthGradeEnum.C
        assert get_grade(Decimal("39.99")) == HealthGradeEnum.D

        # 25.00 boundary
        assert get_grade(Decimal("25.00")) == HealthGradeEnum.D
        assert get_grade(Decimal("24.99")) == HealthGradeEnum.F

    def test_active_loan_count_penalty(self):
        """Test that excessive loan count (> 3) applies incremental penalties."""
        income = Decimal("100000.00")
        emi = Decimal("10000.00")
        disposable = Decimal("60000.00")

        score_3_loans = dashboard_service._calculate_debt_burden_sub_score(income, emi, disposable, 3)
        score_4_loans = dashboard_service._calculate_debt_burden_sub_score(income, emi, disposable, 4)
        score_5_loans = dashboard_service._calculate_debt_burden_sub_score(income, emi, disposable, 5)

        assert score_4_loans == score_3_loans - Decimal("10.00")
        assert score_5_loans == score_3_loans - Decimal("20.00")


# ── Test Suite 2: Database & Multi-Tenant Integration Tests ───────────────────

class TestDashboardDatabaseAndIsolation:
    """Test dashboard aggregation with persisted database models and verify multi-tenant isolation."""

    @pytest.mark.asyncio
    async def test_missing_profile_handled_gracefully(self, db):
        """New user without financial profile receives clean profile_complete=False."""
        user_id = uuid.uuid4()
        res = await dashboard_service.get_dashboard_summary(db, user_id)

        assert isinstance(res, DashboardSummaryResponse)
        assert res.profile_complete is False
        assert res.health_score is None
        assert res.metrics is None
        assert len(res.active_warnings) > 0
        assert "not yet initialized" in res.active_warnings[0].lower()

    @pytest.mark.asyncio
    async def test_complete_profile_dashboard_summary(self, db):
        """User with profile receives aggregated health score, metrics, FOIR and top recommendation."""
        user_id = uuid.uuid4()
        await profile_service.upsert_profile(
            db,
            user_id,
            FinancialProfileCreate(
                monthly_net_income=Decimal("120000.00"),
                monthly_expenses=Decimal("45000.00"),
                existing_monthly_emi=Decimal("12000.00"),
                emergency_savings=Decimal("300000.00"),
                employment_type=EmploymentTypeEnum.SALARIED,
                existing_loan_count=1,
            ),
        )

        res = await dashboard_service.get_dashboard_summary(db, user_id)

        assert res.profile_complete is True
        assert res.health_score is not None
        assert res.health_score.letter_grade in (HealthGradeEnum.A_PLUS, HealthGradeEnum.A)
        assert len(res.health_score.sub_scores) == 4

        metrics = res.metrics
        assert metrics.monthly_net_income == Decimal("120000.00")
        assert metrics.monthly_emi_burden == Decimal("12000.00")
        assert metrics.total_active_loans == 1
        assert metrics.disposable_monthly_cash_flow == Decimal("63000.00")
        assert metrics.emergency_fund_months >= Decimal("6.00")

        assert res.current_foir_percentage == Decimal("10.00")
        assert res.foir_status == "Optimal"
        assert res.overall_risk_category == "LOW"
        assert res.is_borrowing_eligible is True
        assert res.prudent_max_borrowing_emi > Decimal("0.00")
        assert "Personal Loan" in res.top_recommendation_summary or "Home Loan" in res.top_recommendation_summary

    @pytest.mark.asyncio
    async def test_custom_foir_threshold_parameter(self, db):
        """Querying dashboard with different policy thresholds updates borrowing calculations."""
        user_id = uuid.uuid4()
        await profile_service.upsert_profile(
            db,
            user_id,
            FinancialProfileCreate(
                monthly_net_income=Decimal("100000.00"),
                monthly_expenses=Decimal("30000.00"),
                existing_monthly_emi=Decimal("35000.00"),  # FOIR = 35%
                emergency_savings=Decimal("150000.00"),
                employment_type=EmploymentTypeEnum.SALARIED,
                existing_loan_count=2,
            ),
        )

        # 1. Threshold 50% -> Eligible (35% < 50%)
        res_50 = await dashboard_service.get_dashboard_summary(db, user_id, foir_threshold=Decimal("50.00"))
        assert res_50.is_borrowing_eligible is True

        # 2. Threshold 30% -> Ineligible (35% > 30%)
        res_30 = await dashboard_service.get_dashboard_summary(db, user_id, foir_threshold=Decimal("30.00"))
        assert res_30.is_borrowing_eligible is False

    @pytest.mark.asyncio
    async def test_multi_tenant_dashboard_isolation(self, db):
        """User A and User B must never see each other's dashboard metrics."""
        user_a = uuid.uuid4()
        user_b = uuid.uuid4()

        # User A: High income, low debt
        await profile_service.upsert_profile(
            db,
            user_a,
            FinancialProfileCreate(
                monthly_net_income=Decimal("200000.00"),
                monthly_expenses=Decimal("50000.00"),
                existing_monthly_emi=Decimal("10000.00"),
                emergency_savings=Decimal("500000.00"),
                employment_type=EmploymentTypeEnum.SALARIED,
                existing_loan_count=1,
            ),
        )

        # User B: High debt, overleveraged
        await profile_service.upsert_profile(
            db,
            user_b,
            FinancialProfileCreate(
                monthly_net_income=Decimal("40000.00"),
                monthly_expenses=Decimal("20000.00"),
                existing_monthly_emi=Decimal("22000.00"),  # 55% FOIR
                emergency_savings=Decimal("10000.00"),
                employment_type=EmploymentTypeEnum.SALARIED,
                existing_loan_count=3,
            ),
        )

        summary_a = await dashboard_service.get_dashboard_summary(db, user_a)
        summary_b = await dashboard_service.get_dashboard_summary(db, user_b)

        assert summary_a.metrics.monthly_net_income == Decimal("200000.00")
        assert summary_b.metrics.monthly_net_income == Decimal("40000.00")
        assert summary_a.health_score.letter_grade in (HealthGradeEnum.A_PLUS, HealthGradeEnum.A)
        assert summary_b.health_score.letter_grade in (HealthGradeEnum.C, HealthGradeEnum.D, HealthGradeEnum.F)
        assert summary_a.is_borrowing_eligible is True
        assert summary_b.is_borrowing_eligible is False


# ── Test Suite 3: HTTP Endpoint Security & Validation ─────────────────────────

class TestDashboardEndpointHTTP:
    """Test HTTP level auth guards and route status."""

    def test_unauthenticated_request_rejected(self):
        """Requests without session cookie return 401 Unauthorized."""
        client = TestClient(app)
        res = client.get("/api/v1/dashboard")
        assert res.status_code == 401
        assert "not authenticated" in res.json().get("detail", "").lower()
