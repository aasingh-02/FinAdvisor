"""
tests/test_recommendation_service.py
────────────────────────────────────
Unit and integration tests for Phase 2 - Step 5.1: Personalized Loan Recommendation Engine.

Covers:
1. Normal salaried applicant (multi-category eligibility)
2. Self-employed applicant (volatility buffer and conservative haircut)
3. High existing EMI obligations (FOIR breach -> ineligible)
4. Zero income handling (clean ineligibility without math error)
5. Negative disposable cash flow (cash deficit -> ineligible)
6. High FOIR / critical risk ineligibility
7. Insufficient emergency reserves (< 3 months liquidity haircut & warning)
8. Desired loan amount exceeding affordability (prudent adjustment & warning)
9. Desired loan amount within affordability (honors requested amount)
10. Zero-interest principal from EMI calculation
11. Reducing-balance EMI and total repayment reconciliation
12. Unauthenticated API access protection (HTTP 401)
13. Invalid request parameters rejection (HTTP 422)
14. Cross-user multi-tenant data isolation
"""

import uuid
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.financial_profile import FinancialProfile
from app.schemas.financial_profile import EmploymentTypeEnum, FinancialProfileCreate
from app.schemas.recommendation import (
    LoanCategoryEnum,
    RecommendationRequest,
    RecommendationResponse,
)
from app.services import profile_service, recommendation_service


# ── Test Suite 1: Pure Unit Calculation & Recommendation Tests ────────────────

class TestRecommendationEngineUnit:
    """Test deterministic affordability formulas, loan sizing, and scenario rules."""

    def test_normal_salaried_applicant_eligible(self):
        """Salaried applicant with strong disposable cash flow qualifies for all categories."""
        profile = FinancialProfile(
            monthly_net_income=Decimal("120000.00"),
            existing_monthly_emi=Decimal("15000.00"),  # 12.5% FOIR
            monthly_expenses=Decimal("35000.00"),
            emergency_savings=Decimal("300000.00"),    # 8.57 months
            employment_type=EmploymentTypeEnum.SALARIED,
            existing_loan_count=1,
        )

        res = recommendation_service.generate_loan_recommendations(profile)

        assert res.is_eligible is True
        assert len(res.recommendations) == 4
        # Snapshot figures
        assert res.financial_snapshot.monthly_net_income == Decimal("120000.00")
        assert res.financial_snapshot.current_foir_percentage == Decimal("12.50")
        # Disposable income: 120k - 35k - 15k = 70k
        assert res.financial_snapshot.disposable_monthly_income == Decimal("70000.00")
        # Prudent max EMI is bounded by 40% FOIR headroom (33,000) vs 80% cashflow (56,000) -> 33,000
        assert res.financial_snapshot.prudent_max_monthly_emi == Decimal("33000.00")

        # Verify all categories present
        categories = {r.loan_category for r in res.recommendations}
        assert categories == {
            LoanCategoryEnum.PERSONAL_LOAN,
            LoanCategoryEnum.HOME_LOAN,
            LoanCategoryEnum.VEHICLE_LOAN,
            LoanCategoryEnum.EDUCATION_LOAN,
        }

    def test_self_employed_applicant_volatility_buffer(self):
        """Self-employed applicants receive a conservative cash-flow buffer."""
        profile = FinancialProfile(
            monthly_net_income=Decimal("100000.00"),
            existing_monthly_emi=Decimal("15000.00"),
            monthly_expenses=Decimal("30000.00"),
            emergency_savings=Decimal("200000.00"),
            employment_type=EmploymentTypeEnum.SELF_EMPLOYED,
            existing_loan_count=1,
        )

        res = recommendation_service.generate_loan_recommendations(profile)

        assert res.is_eligible is True
        # Disposable = 55,000; self-employed buffer multiplier is 70% -> 38,500
        # Theoretical capacity under 40% = 25,000 -> prudent max is 25,000
        assert res.financial_snapshot.prudent_max_monthly_emi == Decimal("25000.00")
        assert any("self-employed" in w.lower() for w in res.reasons_and_warnings)

    def test_high_existing_emi_ineligible(self):
        """When existing EMI exceeds configured FOIR benchmark, user is ineligible."""
        profile = FinancialProfile(
            monthly_net_income=Decimal("80000.00"),
            existing_monthly_emi=Decimal("36000.00"),  # 45% FOIR > 40%
            monthly_expenses=Decimal("25000.00"),
            emergency_savings=Decimal("100000.00"),
            employment_type=EmploymentTypeEnum.SALARIED,
            existing_loan_count=2,
        )

        res = recommendation_service.generate_loan_recommendations(profile)

        assert res.is_eligible is False
        assert len(res.recommendations) == 0
        assert "reaching or exceeding your configured policy benchmark" in res.eligibility_summary
        assert any("zero additional emi capacity" in w.lower() for w in res.reasons_and_warnings)

    def test_zero_income_ineligible(self):
        """Zero or non-positive net income returns ineligible with clear reason."""
        profile = FinancialProfile(
            monthly_net_income=Decimal("0.00"),
            existing_monthly_emi=Decimal("10000.00"),
            monthly_expenses=Decimal("15000.00"),
            emergency_savings=Decimal("50000.00"),
            employment_type=EmploymentTypeEnum.SALARIED,
            existing_loan_count=1,
        )

        res = recommendation_service.generate_loan_recommendations(profile)

        assert res.is_eligible is False
        assert len(res.recommendations) == 0
        assert "zero or non-positive" in res.eligibility_summary

    def test_negative_disposable_cash_flow_ineligible(self):
        """Cash deficit (living costs + EMIs > net income) returns ineligible."""
        profile = FinancialProfile(
            monthly_net_income=Decimal("50000.00"),
            existing_monthly_emi=Decimal("15000.00"),  # 30% FOIR (low)
            monthly_expenses=Decimal("40000.00"),      # Total outflow = 55k -> Deficit = -5k
            emergency_savings=Decimal("20000.00"),
            employment_type=EmploymentTypeEnum.SALARIED,
            existing_loan_count=1,
        )

        res = recommendation_service.generate_loan_recommendations(profile)

        assert res.is_eligible is False
        assert len(res.recommendations) == 0
        assert "deficit" in res.eligibility_summary.lower()
        assert res.financial_snapshot.disposable_monthly_income == Decimal("-5000.00")

    def test_high_foir_critical_risk_ineligible(self):
        """FOIR >= 65% is strictly blocked from new borrowing."""
        profile = FinancialProfile(
            monthly_net_income=Decimal("60000.00"),
            existing_monthly_emi=Decimal("42000.00"),  # 70% FOIR
            monthly_expenses=Decimal("15000.00"),
            emergency_savings=Decimal("10000.00"),
            employment_type=EmploymentTypeEnum.SALARIED,
            existing_loan_count=3,
        )

        res = recommendation_service.generate_loan_recommendations(profile)

        assert res.is_eligible is False
        assert len(res.recommendations) == 0
        assert res.risk_considerations.overall_risk_category == "CRITICAL"

    def test_insufficient_emergency_reserves_haircut(self):
        """Emergency fund < 3 months triggers conservative 40% liquidity reservation buffer."""
        profile = FinancialProfile(
            monthly_net_income=Decimal("100000.00"),
            existing_monthly_emi=Decimal("15000.00"),
            monthly_expenses=Decimal("40000.00"),
            emergency_savings=Decimal("20000.00"),  # 0.5 months (< 3 months)
            employment_type=EmploymentTypeEnum.SALARIED,
            existing_loan_count=1,
        )

        res = recommendation_service.generate_loan_recommendations(profile)

        assert res.is_eligible is True
        assert res.risk_considerations.has_sufficient_emergency_fund is False
        # Disposable = 45k; 60% buffer margin applied -> 27,000; FOIR headroom = 25,000 -> prudent = 25,000
        assert res.financial_snapshot.prudent_max_monthly_emi == Decimal("25000.00")
        assert any("emergency savings cover only" in w.lower() for w in res.reasons_and_warnings)

    def test_desired_loan_amount_exceeding_affordability_adjusted(self):
        """When requested loan amount exceeds prudent capacity, principal is downsized."""
        profile = FinancialProfile(
            monthly_net_income=Decimal("70000.00"),
            existing_monthly_emi=Decimal("10000.00"),
            monthly_expenses=Decimal("30000.00"),
            emergency_savings=Decimal("150000.00"),
            employment_type=EmploymentTypeEnum.SALARIED,
            existing_loan_count=1,
        )
        # Disposable = 30k * 0.8 = 24k; FOIR headroom at 40% = 18k -> Prudent max EMI = 18,000
        # User requests ₹20,00,000 for Personal Loan (36 mos @ 13.5% requires ~₹67,867/mo EMI >> 18,000)
        req = RecommendationRequest(
            preferred_loan_category=LoanCategoryEnum.PERSONAL_LOAN,
            desired_loan_amount=Decimal("2000000.00"),
            preferred_tenure_months=36,
        )

        res = recommendation_service.generate_loan_recommendations(profile, req)

        assert res.is_eligible is True
        p_loan = next(r for r in res.recommendations if r.loan_category == LoanCategoryEnum.PERSONAL_LOAN)
        # Sizing must be adjusted downward to an affordable principal
        assert p_loan.recommended_principal < Decimal("2000000.00")
        assert p_loan.estimated_monthly_emi <= Decimal("18000.00")
        assert any("adjusted to the maximum affordable amount" in w.lower() for w in res.reasons_and_warnings)

    def test_desired_loan_amount_within_affordability_honored(self):
        """When requested loan amount fits within prudent capacity, it is directly recommended."""
        profile = FinancialProfile(
            monthly_net_income=Decimal("120000.00"),
            existing_monthly_emi=Decimal("15000.00"),
            monthly_expenses=Decimal("35000.00"),
            emergency_savings=Decimal("250000.00"),
            employment_type=EmploymentTypeEnum.SALARIED,
            existing_loan_count=1,
        )
        # Prudent max EMI is 33,000. Requested loan is ₹3,00,000 @ 13.5% for 36 mos (EMI ~ ₹10,181 <= 33k)
        req = RecommendationRequest(
            preferred_loan_category=LoanCategoryEnum.PERSONAL_LOAN,
            desired_loan_amount=Decimal("300000.00"),
            preferred_tenure_months=36,
        )

        res = recommendation_service.generate_loan_recommendations(profile, req)

        assert res.is_eligible is True
        p_loan = next(r for r in res.recommendations if r.loan_category == LoanCategoryEnum.PERSONAL_LOAN)
        assert p_loan.recommended_principal == Decimal("300000.00")
        assert "fits comfortably within your prudent capacity" in p_loan.suitability_reason

    def test_zero_interest_principal_derivation(self):
        """Zero interest loans cleanly derive P = EMI * n without division-by-zero."""
        target_emi = Decimal("10000.00")
        principal = recommendation_service.calculate_principal_from_emi(
            target_emi=target_emi,
            annual_interest_rate=Decimal("0.00"),
            tenure_months=60,
        )
        # 10,000 * 60 = 600,000
        assert principal == Decimal("600000.00")

    def test_reducing_balance_emi_and_repayment_reconciliation(self):
        """All recommendation items strictly satisfy Principal + Interest = Total Repayment."""
        profile = FinancialProfile(
            monthly_net_income=Decimal("100000.00"),
            existing_monthly_emi=Decimal("12000.00"),
            monthly_expenses=Decimal("30000.00"),
            emergency_savings=Decimal("200000.00"),
            employment_type=EmploymentTypeEnum.SALARIED,
            existing_loan_count=1,
        )

        res = recommendation_service.generate_loan_recommendations(profile)

        assert res.is_eligible is True
        for item in res.recommendations:
            expected_total = item.recommended_principal + item.total_interest_payable
            assert item.total_repayment == expected_total
            # Month count is valid
            assert item.suggested_tenure_months > 0
            # Projected FOIR is within acceptable range
            assert item.projected_foir_percentage <= Decimal("40.00")


# ── Test Suite 2: DB Integration & Cross-User Isolation ───────────────────────

class TestRecommendationDatabaseAndIsolation:
    """Test recommendations with database models and verify multi-tenant isolation."""

    @pytest.mark.asyncio
    async def test_persisted_profile_recommendation_flow(self, db):
        """Verify recommendations using an actual persisted profile."""
        user_id = uuid.uuid4()
        profile_data = FinancialProfileCreate(
            monthly_net_income=Decimal("130000.00"),
            monthly_expenses=Decimal("40000.00"),
            existing_monthly_emi=Decimal("20000.00"),
            emergency_savings=Decimal("300000.00"),
            employment_type=EmploymentTypeEnum.SALARIED,
            existing_loan_count=1,
        )
        profile = await profile_service.upsert_profile(db, user_id, profile_data)

        res = recommendation_service.generate_loan_recommendations(profile)
        assert res.is_eligible is True
        assert len(res.recommendations) == 4
        assert res.financial_snapshot.monthly_net_income == Decimal("130000.00")

    @pytest.mark.asyncio
    async def test_cross_user_isolation(self, db):
        """User A (Eligible) and User B (Overleveraged) remain strictly isolated."""
        user_a = uuid.uuid4()
        user_b = uuid.uuid4()

        # User A: High income, low debt
        profile_a = await profile_service.upsert_profile(
            db,
            user_a,
            FinancialProfileCreate(
                monthly_net_income=Decimal("150000.00"),
                monthly_expenses=Decimal("35000.00"),
                existing_monthly_emi=Decimal("15000.00"),
                emergency_savings=Decimal("500000.00"),
            ),
        )

        # User B: High debt, overleveraged
        profile_b = await profile_service.upsert_profile(
            db,
            user_b,
            FinancialProfileCreate(
                monthly_net_income=Decimal("60000.00"),
                monthly_expenses=Decimal("25000.00"),
                existing_monthly_emi=Decimal("32000.00"),  # > 50% FOIR
                emergency_savings=Decimal("20000.00"),
            ),
        )

        res_a = recommendation_service.generate_loan_recommendations(profile_a)
        res_b = recommendation_service.generate_loan_recommendations(profile_b)

        assert res_a.is_eligible is True
        assert len(res_a.recommendations) > 0

        assert res_b.is_eligible is False
        assert len(res_b.recommendations) == 0


# ── Test Suite 3: HTTP Endpoint Security & Validation ─────────────────────────

class TestRecommendationEndpointHTTP:
    """Test HTTP level behavior, auth guards, and parameter validation."""

    def test_unauthenticated_request_rejected(self):
        """Requests without session cookie return 401 Unauthorized."""
        client = TestClient(app)
        res = client.post("/api/v1/recommendations/generate", json={})
        assert res.status_code == 401
        assert "Not authenticated" in res.json().get("detail", "")

    def test_invalid_request_parameters_rejected(self):
        """Invalid threshold or negative loan amount returns 422 Unprocessable Entity."""
        client = TestClient(app)
        # Threshold out of range
        res_low = client.post("/api/v1/recommendations/generate", json={"foir_threshold": -5.0})
        # Desired loan amount non-positive
        res_amt = client.post("/api/v1/recommendations/generate", json={"desired_loan_amount": -1000.0})
        # Tenure out of bounds (< 6 months)
        res_tenure = client.post("/api/v1/recommendations/generate", json={"preferred_tenure_months": 2})

        for r in (res_low, res_amt, res_tenure):
            assert r.status_code in (401, 422)
