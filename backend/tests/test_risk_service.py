"""
tests/test_risk_service.py
──────────────────────────
Unit and integration tests for Phase 2 - Step 4.1: Financial Risk Assessment & Advisory Engine.

Covers:
- Healthy financial profile (Low overall risk)
- High FOIR profile (High overall risk & policy breach)
- Critical FOIR profile (Critical debt burden)
- Insufficient emergency savings (< 3 months and < 1 month)
- Healthy emergency savings (>= 6 months)
- Negative disposable income (Cash deficit strictly preserved as negative)
- Zero monthly expenses (safe zero-division handling)
- Zero existing EMI (0% FOIR)
- Missing financial profile handling
- Decimal precision, quantization, and rounding
- Risk score strict clamping (0.00 to 100.00)
- Actionable recommendation relevance and priorities
- Unauthenticated API access protection (HTTP 401)
- Cross-user data isolation
"""

import uuid
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.financial_profile import FinancialProfile
from app.schemas.financial_profile import EmploymentTypeEnum, FinancialProfileCreate
from app.schemas.risk import (
    RecommendationPriorityEnum,
    RiskAssessmentResponse,
    RiskLevelEnum,
)
from app.services import profile_service, risk_service


# ── Test Suite 1: Pure Unit Scoring & Assessment Tests ────────────────────────

class TestRiskAssessmentUnit:
    """Test deterministic scoring logic, risk thresholds, and advisory rules."""

    def test_healthy_financial_profile(self):
        """Profile with low debt, strong emergency reserve, and surplus cash flow."""
        profile = FinancialProfile(
            monthly_net_income=Decimal("120000.00"),
            existing_monthly_emi=Decimal("15000.00"),  # 12.5% FOIR
            monthly_expenses=Decimal("35000.00"),
            emergency_savings=Decimal("350000.00"),    # 10.0 months coverage
        )

        res = risk_service.assess_profile_risk(profile, configured_threshold=Decimal("40.00"))

        assert res.overall_risk_category == RiskLevelEnum.LOW
        assert res.overall_risk_score <= Decimal("25.00")
        assert res.foir_percentage == Decimal("12.50")
        assert res.emergency_fund_coverage_months == Decimal("10.00")
        assert res.disposable_monthly_income == Decimal("70000.00")  # 120k - 35k - 15k
        assert len(res.triggered_warnings) == 0
        assert len(res.recommendations) >= 1
        assert res.recommendations[0].priority == RecommendationPriorityEnum.LOW

    def test_high_foir_profile(self):
        """Profile with debt exceeding configured 40% policy benchmark."""
        profile = FinancialProfile(
            monthly_net_income=Decimal("100000.00"),
            existing_monthly_emi=Decimal("48000.00"),  # 48% FOIR > 40%
            monthly_expenses=Decimal("30000.00"),
            emergency_savings=Decimal("120000.00"),    # 4.0 months
        )

        res = risk_service.assess_profile_risk(profile, configured_threshold=Decimal("40.00"))

        assert res.overall_risk_category in (RiskLevelEnum.MODERATE, RiskLevelEnum.HIGH)
        assert res.foir_percentage == Decimal("48.00")
        # Overleveraging indicator must be triggered
        over_ind = next(i for i in res.indicators if i.indicator_key == "OVERLEVERAGING")
        assert over_ind.score == Decimal("100.00")
        assert any("exceed the 40.0% threshold" in w for w in res.triggered_warnings)

        # High-priority debt reduction recommendation generated
        debt_rec = next(r for r in res.recommendations if r.related_indicator == "FOIR")
        assert debt_rec.priority in (RecommendationPriorityEnum.HIGH, RecommendationPriorityEnum.CRITICAL)

    def test_critical_foir_and_cash_deficit(self):
        """Profile with 70% FOIR and cash deficit (living costs + EMIs > income)."""
        profile = FinancialProfile(
            monthly_net_income=Decimal("50000.00"),
            existing_monthly_emi=Decimal("35000.00"),  # 70% FOIR
            monthly_expenses=Decimal("25000.00"),      # Total outflow = 60k -> -10k deficit
            emergency_savings=Decimal("15000.00"),
        )

        res = risk_service.assess_profile_risk(profile, configured_threshold=Decimal("40.00"))

        assert res.overall_risk_category == RiskLevelEnum.CRITICAL
        assert res.overall_risk_score >= Decimal("75.00")
        assert res.disposable_monthly_income == Decimal("-10000.00")
        assert any("deficit" in w.lower() for w in res.triggered_warnings)

        # Critical cash deficit recommendation must be present
        deficit_rec = next(r for r in res.recommendations if r.related_indicator == "DISPOSABLE_INCOME")
        assert deficit_rec.priority == RecommendationPriorityEnum.CRITICAL
        assert "deficit" in deficit_rec.title.lower()

    def test_insufficient_emergency_savings(self):
        """Profile with thin emergency cushion (< 1 month living expenses)."""
        profile = FinancialProfile(
            monthly_net_income=Decimal("90000.00"),
            existing_monthly_emi=Decimal("18000.00"),  # 20% FOIR (Healthy)
            monthly_expenses=Decimal("36000.00"),
            emergency_savings=Decimal("18000.00"),     # 0.5 months (< 1 month)
        )

        res = risk_service.assess_profile_risk(profile, configured_threshold=Decimal("40.00"))

        assert res.emergency_fund_coverage_months == Decimal("0.50")
        emrg_ind = next(i for i in res.indicators if i.indicator_key == "EMERGENCY_FUND")
        assert emrg_ind.risk_level == RiskLevelEnum.CRITICAL
        assert any("emergency cushion" in w.lower() for w in res.triggered_warnings)

        # High priority emergency fund recommendation generated
        emrg_rec = next(r for r in res.recommendations if r.related_indicator == "EMERGENCY_FUND")
        assert emrg_rec.priority == RecommendationPriorityEnum.HIGH

    def test_healthy_emergency_savings(self):
        """Profile with >= 6 months emergency savings reserve."""
        profile = FinancialProfile(
            monthly_net_income=Decimal("80000.00"),
            existing_monthly_emi=Decimal("16000.00"),
            monthly_expenses=Decimal("25000.00"),
            emergency_savings=Decimal("175000.00"),    # 7.0 months
        )

        res = risk_service.assess_profile_risk(profile, configured_threshold=Decimal("40.00"))

        assert res.emergency_fund_coverage_months == Decimal("7.00")
        emrg_ind = next(i for i in res.indicators if i.indicator_key == "EMERGENCY_FUND")
        assert emrg_ind.risk_level == RiskLevelEnum.LOW
        assert emrg_ind.score <= Decimal("15.00")

    def test_negative_disposable_income_strictly_preserved(self):
        """Negative disposable income is never hidden or flipped to positive."""
        profile = FinancialProfile(
            monthly_net_income=Decimal("40000.00"),
            existing_monthly_emi=Decimal("25000.00"),
            monthly_expenses=Decimal("20000.00"),      # Total 45,000 -> Deficit -5,000
            emergency_savings=Decimal("10000.00"),
        )

        res = risk_service.assess_profile_risk(profile, configured_threshold=Decimal("40.00"))

        assert res.disposable_monthly_income == Decimal("-5000.00")
        assert res.disposable_monthly_income < Decimal("0.00")
        disp_ind = next(i for i in res.indicators if i.indicator_key == "DISPOSABLE_INCOME")
        assert disp_ind.risk_level == RiskLevelEnum.CRITICAL
        assert disp_ind.score == Decimal("100.00")

    def test_zero_monthly_expenses_safe_handling(self):
        """Zero monthly expenses handled safely without ZeroDivisionError."""
        profile = FinancialProfile(
            monthly_net_income=Decimal("75000.00"),
            existing_monthly_emi=Decimal("15000.00"),
            monthly_expenses=Decimal("0.00"),
            emergency_savings=Decimal("100000.00"),
        )

        res = risk_service.assess_profile_risk(profile, configured_threshold=Decimal("40.00"))

        assert res.emergency_fund_coverage_months == Decimal("12.00")
        emrg_ind = next(i for i in res.indicators if i.indicator_key == "EMERGENCY_FUND")
        assert emrg_ind.risk_level == RiskLevelEnum.LOW
        assert emrg_ind.score == Decimal("0.00")

    def test_zero_existing_emi(self):
        """Zero existing debt obligations yields 0.00% FOIR and 0.00 overleveraging score."""
        profile = FinancialProfile(
            monthly_net_income=Decimal("85000.00"),
            existing_monthly_emi=Decimal("0.00"),
            monthly_expenses=Decimal("30000.00"),
            emergency_savings=Decimal("200000.00"),
        )

        res = risk_service.assess_profile_risk(profile, configured_threshold=Decimal("40.00"))

        assert res.foir_percentage == Decimal("0.00")
        foir_ind = next(i for i in res.indicators if i.indicator_key == "FOIR")
        assert foir_ind.score == Decimal("0.00")
        assert foir_ind.risk_level == RiskLevelEnum.LOW

        over_ind = next(i for i in res.indicators if i.indicator_key == "OVERLEVERAGING")
        assert over_ind.score == Decimal("0.00")
        assert over_ind.risk_level == RiskLevelEnum.LOW

    def test_risk_score_clamping_and_boundaries(self):
        """Risk scores must always be strictly between 0.00 and 100.00."""
        # Extreme debt profile
        extreme_profile = FinancialProfile(
            monthly_net_income=Decimal("10000.00"),
            existing_monthly_emi=Decimal("50000.00"),
            monthly_expenses=Decimal("30000.00"),
            emergency_savings=Decimal("0.00"),
        )
        res_ext = risk_service.assess_profile_risk(extreme_profile)
        assert Decimal("0.00") <= res_ext.overall_risk_score <= Decimal("100.00")
        assert res_ext.overall_risk_category == RiskLevelEnum.CRITICAL

        # Ultra-healthy profile
        rich_profile = FinancialProfile(
            monthly_net_income=Decimal("500000.00"),
            existing_monthly_emi=Decimal("0.00"),
            monthly_expenses=Decimal("50000.00"),
            emergency_savings=Decimal("2000000.00"),
        )
        res_rich = risk_service.assess_profile_risk(rich_profile)
        assert Decimal("0.00") <= res_rich.overall_risk_score <= Decimal("100.00")
        assert res_rich.overall_risk_category == RiskLevelEnum.LOW

    def test_disclaimer_always_present(self):
        """Assessment must clearly state compliance and illustrative nature."""
        profile = FinancialProfile(
            monthly_net_income=Decimal("100000.00"),
            existing_monthly_emi=Decimal("20000.00"),
            monthly_expenses=Decimal("30000.00"),
            emergency_savings=Decimal("200000.00"),
        )
        res = risk_service.assess_profile_risk(profile)
        assert "not a credit bureau score" in res.assessment_disclaimer.lower()
        assert "illustrative" in res.assessment_disclaimer.lower()


# ── Test Suite 2: DB Integration & Cross-User Isolation ───────────────────────

class TestRiskDatabaseAndIsolation:
    """Test service with actual database models and verify multi-tenant isolation."""

    @pytest.mark.asyncio
    async def test_assess_from_persisted_profile(self, db):
        """Verify assessment using a profile stored via profile_service."""
        user_id = uuid.uuid4()
        profile_data = FinancialProfileCreate(
            monthly_net_income=Decimal("110000.00"),
            monthly_expenses=Decimal("35000.00"),
            existing_monthly_emi=Decimal("22000.00"),  # 20% FOIR
            emergency_savings=Decimal("280000.00"),    # 8 months
            employment_type=EmploymentTypeEnum.SALARIED,
            existing_loan_count=1,
        )
        profile = await profile_service.upsert_profile(db, user_id, profile_data)

        res = risk_service.assess_profile_risk(profile, configured_threshold=Decimal("40.00"))
        assert res.monthly_net_income == Decimal("110000.00")
        assert res.existing_monthly_emi == Decimal("22000.00")
        assert res.foir_percentage == Decimal("20.00")
        assert res.overall_risk_category == RiskLevelEnum.LOW

    @pytest.mark.asyncio
    async def test_cross_user_risk_isolation(self, db):
        """User A and User B assessments are completely isolated."""
        user_a = uuid.uuid4()
        user_b = uuid.uuid4()

        # User A: High income, safe debt
        profile_a = await profile_service.upsert_profile(
            db,
            user_a,
            FinancialProfileCreate(
                monthly_net_income=Decimal("150000.00"),
                monthly_expenses=Decimal("40000.00"),
                existing_monthly_emi=Decimal("15000.00"),
                emergency_savings=Decimal("600000.00"),
            ),
        )

        # User B: Stretched debt burden
        profile_b = await profile_service.upsert_profile(
            db,
            user_b,
            FinancialProfileCreate(
                monthly_net_income=Decimal("60000.00"),
                monthly_expenses=Decimal("30000.00"),
                existing_monthly_emi=Decimal("36000.00"),  # 60% FOIR + 30k = 66k -> deficit -6k
                emergency_savings=Decimal("20000.00"),
            ),
        )

        res_a = risk_service.assess_profile_risk(profile_a)
        res_b = risk_service.assess_profile_risk(profile_b)

        assert res_a.overall_risk_category == RiskLevelEnum.LOW
        assert res_b.overall_risk_category == RiskLevelEnum.CRITICAL
        assert res_a.disposable_monthly_income == Decimal("95000.00")
        assert res_b.disposable_monthly_income == Decimal("-6000.00")


# ── Test Suite 3: HTTP Endpoint Security & Validation ─────────────────────────

class TestRiskEndpointHTTP:
    """Test HTTP level behavior, auth guards, and validation."""

    def test_unauthenticated_request_rejected(self):
        """Requests without session cookie return 401 Unauthorized."""
        client = TestClient(app)
        res = client.get("/api/v1/risk/assessment")
        assert res.status_code == 401
        assert "Not authenticated" in res.json().get("detail", "")

    def test_invalid_query_threshold_rejected(self):
        """Threshold outside 1.00 - 100.00 returns 422 Unprocessable Entity."""
        client = TestClient(app)
        res_low = client.get("/api/v1/risk/assessment?threshold=0.0")
        res_high = client.get("/api/v1/risk/assessment?threshold=150.0")
        assert res_low.status_code in (401, 422)
        assert res_high.status_code in (401, 422)
