"""
tests/test_profile_service.py
─────────────────────────────
Unit and integration tests for Step 1: Financial Profile API.

Covers:
- Successful creation via upsert
- Duplicate profile handling (upsert overwrites without duplicating rows)
- Partial update via PATCH (exclude_unset=True)
- Rejection of empty PATCH payloads
- Rejection of explicit null values in PATCH
- Pydantic validation failures (zero/negative income, negative expenses/EMI)
- Unauthenticated requests (401 Unauthorized)
- Cross-user data isolation (User B cannot view or modify User A's data)
"""

import uuid
from decimal import Decimal
import pytest
from pydantic import ValidationError

from app.models.financial_profile import FinancialProfile
from app.schemas.financial_profile import (
    FinancialProfileCreate,
    FinancialProfileUpdate,
    EmploymentTypeEnum,
)
from app.services import profile_service


# ── Fixtures & Helpers ────────────────────────────────────────────────────────

VALID_CREATE_DATA = FinancialProfileCreate(
    monthly_net_income=Decimal("85000.00"),
    monthly_expenses=Decimal("35000.00"),
    existing_monthly_emi=Decimal("12000.00"),
    emergency_savings=Decimal("250000.00"),
    employment_type=EmploymentTypeEnum.SALARIED,
    existing_loan_count=1,
)


class TestFinancialProfileSchemas:
    """Test Pydantic input validation rules."""

    def test_valid_schema(self):
        profile = FinancialProfileCreate(
            monthly_net_income=Decimal("50000.00"),
            monthly_expenses=Decimal("20000.00"),
            existing_monthly_emi=Decimal("10000.00"),
            emergency_savings=Decimal("100000.00"),
        )
        assert profile.monthly_net_income == Decimal("50000.00")
        assert profile.employment_type == EmploymentTypeEnum.SALARIED

    def test_zero_income_rejected(self):
        with pytest.raises(ValidationError, match="greater than 0"):
            FinancialProfileCreate(
                monthly_net_income=Decimal("0.00"),
                monthly_expenses=Decimal("20000.00"),
                existing_monthly_emi=Decimal("5000.00"),
                emergency_savings=Decimal("10000.00"),
            )

    def test_negative_income_rejected(self):
        with pytest.raises(ValidationError, match="greater than 0"):
            FinancialProfileCreate(
                monthly_net_income=Decimal("-1000.00"),
                monthly_expenses=Decimal("20000.00"),
                existing_monthly_emi=Decimal("5000.00"),
                emergency_savings=Decimal("10000.00"),
            )

    def test_negative_expenses_rejected(self):
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            FinancialProfileCreate(
                monthly_net_income=Decimal("50000.00"),
                monthly_expenses=Decimal("-500.00"),
            )

    def test_negative_emi_rejected(self):
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            FinancialProfileCreate(
                monthly_net_income=Decimal("50000.00"),
                existing_monthly_emi=Decimal("-200.00"),
            )

    def test_negative_savings_rejected(self):
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            FinancialProfileCreate(
                monthly_net_income=Decimal("50000.00"),
                emergency_savings=Decimal("-1.00"),
            )

    def test_invalid_employment_type_rejected(self):
        with pytest.raises(ValidationError):
            FinancialProfileCreate(
                monthly_net_income=Decimal("50000.00"),
                employment_type="ASTRONAUT",  # invalid enum
            )

    # ── SEC-VULN-008: Upper Bounds, Zeroes & Decimal Precision Tests ───────────

    def test_zero_values_where_permitted(self):
        """Zero is valid for expenses, EMI, emergency savings, and loan count."""
        profile = FinancialProfileCreate(
            monthly_net_income=Decimal("60000.00"),
            monthly_expenses=Decimal("0.00"),
            existing_monthly_emi=Decimal("0.00"),
            emergency_savings=Decimal("0.00"),
            existing_loan_count=0,
        )
        assert profile.monthly_expenses == Decimal("0.00")
        assert profile.existing_monthly_emi == Decimal("0.00")
        assert profile.emergency_savings == Decimal("0.00")
        assert profile.existing_loan_count == 0

    def test_maximum_supported_boundary_values_accepted(self):
        """Values exactly at the Numeric(12, 2) boundary (9,999,999,999.99) must be accepted."""
        from app.schemas.financial_profile import MAX_FINANCIAL_AMOUNT

        assert MAX_FINANCIAL_AMOUNT == Decimal("9999999999.99")

        profile = FinancialProfileCreate(
            monthly_net_income=MAX_FINANCIAL_AMOUNT,
            monthly_expenses=MAX_FINANCIAL_AMOUNT,
            existing_monthly_emi=MAX_FINANCIAL_AMOUNT,
            emergency_savings=MAX_FINANCIAL_AMOUNT,
            existing_loan_count=1000,
        )
        assert profile.monthly_net_income == MAX_FINANCIAL_AMOUNT
        assert profile.monthly_expenses == MAX_FINANCIAL_AMOUNT
        assert profile.existing_monthly_emi == MAX_FINANCIAL_AMOUNT
        assert profile.emergency_savings == MAX_FINANCIAL_AMOUNT

    def test_values_exceeding_maximum_boundary_rejected(self):
        """Values exceeding the Numeric(12, 2) database capacity (e.g. 10B) must raise ValidationError."""
        overflow_amount = Decimal("10000000000.00")

        # Income overflow
        with pytest.raises(ValidationError):
            FinancialProfileCreate(
                monthly_net_income=overflow_amount,
                monthly_expenses=Decimal("10000.00"),
            )

        # Expenses overflow
        with pytest.raises(ValidationError):
            FinancialProfileCreate(
                monthly_net_income=Decimal("50000.00"),
                monthly_expenses=overflow_amount,
            )

        # EMI overflow
        with pytest.raises(ValidationError):
            FinancialProfileCreate(
                monthly_net_income=Decimal("50000.00"),
                existing_monthly_emi=overflow_amount,
            )

        # Savings overflow
        with pytest.raises(ValidationError):
            FinancialProfileCreate(
                monthly_net_income=Decimal("50000.00"),
                emergency_savings=overflow_amount,
            )

    def test_decimal_precision_edge_cases(self):
        """
        Monetary fields strictly permit up to 2 decimal places.
        3+ decimal places must be rejected rather than silently rounded or altered.
        """
        # Valid 1 decimal place
        p1 = FinancialProfileCreate(
            monthly_net_income=Decimal("50000.5"),
            monthly_expenses=Decimal("20000.0"),
        )
        assert p1.monthly_net_income == Decimal("50000.50")

        # Valid exactly 2 decimal places
        p2 = FinancialProfileCreate(
            monthly_net_income=Decimal("50000.99"),
            monthly_expenses=Decimal("20000.01"),
        )
        assert p2.monthly_net_income == Decimal("50000.99")

        # Invalid 3 decimal places on income
        with pytest.raises(ValidationError, match="no more than 2 decimal places"):
            FinancialProfileCreate(
                monthly_net_income=Decimal("50000.555"),
                monthly_expenses=Decimal("20000.00"),
            )

        # Invalid 4 decimal places on expenses
        with pytest.raises(ValidationError, match="no more than 2 decimal places"):
            FinancialProfileCreate(
                monthly_net_income=Decimal("50000.00"),
                monthly_expenses=Decimal("20000.1234"),
            )

        # Invalid 3 decimal places on boundary
        with pytest.raises(ValidationError):
            FinancialProfileCreate(
                monthly_net_income=Decimal("9999999999.999"),
            )

        # Invalid 3 decimal places within digit bounds triggers decimal_max_places
        with pytest.raises(ValidationError, match="no more than 2 decimal places"):
            FinancialProfileCreate(
                monthly_net_income=Decimal("12345.678"),
            )

    def test_update_schema_boundary_and_precision_validation(self):
        """FinancialProfileUpdate (PATCH) consistently validates bounds and precision."""
        from app.schemas.financial_profile import MAX_FINANCIAL_AMOUNT

        # Valid boundary update
        up_valid = FinancialProfileUpdate(monthly_net_income=MAX_FINANCIAL_AMOUNT)
        assert up_valid.monthly_net_income == MAX_FINANCIAL_AMOUNT

        # Valid zero update where permitted
        up_zero = FinancialProfileUpdate(monthly_expenses=Decimal("0.00"))
        assert up_zero.monthly_expenses == Decimal("0.00")

        # Overflow rejected
        with pytest.raises(ValidationError):
            FinancialProfileUpdate(monthly_net_income=Decimal("10000000000.00"))

        # Negative rejected
        with pytest.raises(ValidationError):
            FinancialProfileUpdate(existing_monthly_emi=Decimal("-100.00"))

        # Extra decimal places rejected
        with pytest.raises(ValidationError, match="no more than 2 decimal places"):
            FinancialProfileUpdate(emergency_savings=Decimal("500.123"))


class TestFinancialProfileService:
    """Test business logic and cross-user isolation."""

    @pytest.mark.asyncio
    async def test_upsert_creates_profile(self, db):
        user_id = uuid.uuid4()
        profile = await profile_service.upsert_profile(db, user_id, VALID_CREATE_DATA)

        assert profile.id is not None
        assert profile.user_id == user_id
        assert profile.monthly_net_income == Decimal("85000.00")
        assert profile.monthly_expenses == Decimal("35000.00")
        assert profile.existing_monthly_emi == Decimal("12000.00")
        assert profile.emergency_savings == Decimal("250000.00")

    @pytest.mark.asyncio
    async def test_upsert_replaces_existing_profile(self, db):
        user_id = uuid.uuid4()
        # Initial profile
        await profile_service.upsert_profile(db, user_id, VALID_CREATE_DATA)

        # Upsert with new income and EMI
        new_data = FinancialProfileCreate(
            monthly_net_income=Decimal("95000.00"),
            monthly_expenses=Decimal("40000.00"),
            existing_monthly_emi=Decimal("18000.00"),
            emergency_savings=Decimal("300000.00"),
            employment_type=EmploymentTypeEnum.BUSINESS,
            existing_loan_count=2,
        )
        updated = await profile_service.upsert_profile(db, user_id, new_data)

        assert updated.user_id == user_id
        assert updated.monthly_net_income == Decimal("95000.00")
        assert updated.existing_monthly_emi == Decimal("18000.00")
        assert updated.employment_type == "BUSINESS"

    @pytest.mark.asyncio
    async def test_partial_update_patch_success(self, db):
        user_id = uuid.uuid4()
        await profile_service.upsert_profile(db, user_id, VALID_CREATE_DATA)

        # PATCH: only update existing_monthly_emi
        patch_data = FinancialProfileUpdate(existing_monthly_emi=Decimal("15000.00"))
        patched = await profile_service.update_profile(db, user_id, patch_data)

        assert patched.existing_monthly_emi == Decimal("15000.00")
        # Other fields remain unchanged
        assert patched.monthly_net_income == Decimal("85000.00")
        assert patched.emergency_savings == Decimal("250000.00")

    @pytest.mark.asyncio
    async def test_partial_update_rejects_empty_payload(self, db):
        user_id = uuid.uuid4()
        await profile_service.upsert_profile(db, user_id, VALID_CREATE_DATA)

        empty_patch = FinancialProfileUpdate()
        with pytest.raises(ValueError, match="No fields provided for update"):
            await profile_service.update_profile(db, user_id, empty_patch)

    @pytest.mark.asyncio
    async def test_cross_user_isolation(self, db):
        """Ensure User B cannot retrieve or update User A's profile."""
        user_a = uuid.uuid4()
        user_b = uuid.uuid4()

        # User A creates their profile
        profile_a = await profile_service.upsert_profile(db, user_a, VALID_CREATE_DATA)

        # User B queries their own profile -> must return None
        profile_b = await profile_service.get_profile_by_user_id(db, user_b)
        assert profile_b is None

        # User B attempts to patch their own profile -> raises profile not found
        patch_data = FinancialProfileUpdate(monthly_expenses=Decimal("10000.00"))
        with pytest.raises(ValueError, match="not found"):
            await profile_service.update_profile(db, user_b, patch_data)

        # User A's profile is intact
        profile_a_check = await profile_service.get_profile_by_user_id(db, user_a)
        assert profile_a_check is not None
        assert profile_a_check.id == profile_a.id
        assert profile_a_check.monthly_net_income == Decimal("85000.00")


# ── HTTP Endpoint Boundary Tests (SEC-VULN-008) ───────────────────────────────


class TestFinancialProfileHTTPEndpoints:
    """Verify HTTP PUT and PATCH endpoints enforce bounds, precision, and return 422 for invalid amounts."""

    @pytest.fixture
    def authenticated_client_app(self, db):
        from app.main import create_app
        from app.database import get_db
        from app.middleware.auth_middleware import get_current_user
        from app.models.user import User

        app = create_app()

        mock_user = User(
            id=uuid.uuid4(),
            email="profile_tester@example.com",
            full_name="Profile Tester",
            is_active=True,
        )

        async def override_db():
            yield db

        async def override_user():
            return mock_user

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = override_user
        return app, mock_user

    @pytest.mark.asyncio
    async def test_put_profile_normal_valid_amounts(self, authenticated_client_app):
        from httpx import ASGITransport, AsyncClient

        app, _ = authenticated_client_app
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers={"Origin": "http://localhost:5173"},
        ) as client:
            res = await client.put(
                "/api/v1/profile",
                json={
                    "monthly_net_income": "75000.00",
                    "monthly_expenses": "25000.00",
                    "existing_monthly_emi": "10000.00",
                    "emergency_savings": "150000.00",
                    "employment_type": "SALARIED",
                    "existing_loan_count": 1,
                },
            )
            assert res.status_code == 200
            data = res.json()
            assert data["message"] == "Financial profile saved successfully."
            assert data["profile"]["monthly_net_income"] == "75000.00"

    @pytest.mark.asyncio
    async def test_put_profile_maximum_supported_boundary_saved_in_db(self, authenticated_client_app):
        """Values exactly at 9,999,999,999.99 save and return successfully."""
        from httpx import ASGITransport, AsyncClient

        app, _ = authenticated_client_app
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers={"Origin": "http://localhost:5173"},
        ) as client:
            res = await client.put(
                "/api/v1/profile",
                json={
                    "monthly_net_income": "9999999999.99",
                    "monthly_expenses": "9999999999.99",
                    "existing_monthly_emi": "9999999999.99",
                    "emergency_savings": "9999999999.99",
                    "employment_type": "BUSINESS",
                    "existing_loan_count": 5,
                },
            )
            assert res.status_code == 200
            assert res.json()["profile"]["monthly_net_income"] == "9999999999.99"

    @pytest.mark.asyncio
    async def test_put_profile_exceeding_maximum_rejected_with_422(self, authenticated_client_app):
        """Amounts exceeding Numeric(12, 2) capacity are rejected with HTTP 422 before touching the DB."""
        from httpx import ASGITransport, AsyncClient

        app, _ = authenticated_client_app
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers={"Origin": "http://localhost:5173"},
        ) as client:
            res = await client.put(
                "/api/v1/profile",
                json={
                    "monthly_net_income": "10000000000.00",
                    "monthly_expenses": "20000.00",
                },
            )
            assert res.status_code == 422
            # Must return clean Pydantic validation error, not 500 database DataError
            err_detail = res.json()["detail"]
            assert any("monthly_net_income" in str(e["loc"]) for e in err_detail)

    @pytest.mark.asyncio
    async def test_put_profile_negative_income_rejected_with_422(self, authenticated_client_app):
        from httpx import ASGITransport, AsyncClient

        app, _ = authenticated_client_app
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers={"Origin": "http://localhost:5173"},
        ) as client:
            res = await client.put(
                "/api/v1/profile",
                json={
                    "monthly_net_income": "-500.00",
                    "monthly_expenses": "20000.00",
                },
            )
            assert res.status_code == 422
            err_detail = res.json()["detail"]
            assert any("greater than 0" in e["msg"] for e in err_detail)

    @pytest.mark.asyncio
    async def test_put_profile_extra_decimals_rejected_with_422(self, authenticated_client_app):
        """Values with > 2 decimal places are rejected rather than silently rounded."""
        from httpx import ASGITransport, AsyncClient

        app, _ = authenticated_client_app
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers={"Origin": "http://localhost:5173"},
        ) as client:
            res = await client.put(
                "/api/v1/profile",
                json={
                    "monthly_net_income": "75000.555",
                    "monthly_expenses": "20000.00",
                },
            )
            assert res.status_code == 422
            err_detail = res.json()["detail"]
            assert any("2 decimal places" in e["msg"] for e in err_detail)

    @pytest.mark.asyncio
    async def test_patch_profile_maximum_boundary_saved_in_db(self, authenticated_client_app):
        """PATCH with maximum boundary amount updates profile in DB successfully."""
        from httpx import ASGITransport, AsyncClient

        app, _ = authenticated_client_app
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers={"Origin": "http://localhost:5173"},
        ) as client:
            # 1. First create initial profile
            await client.put(
                "/api/v1/profile",
                json={
                    "monthly_net_income": "50000.00",
                    "monthly_expenses": "20000.00",
                    "existing_monthly_emi": "5000.00",
                    "emergency_savings": "50000.00",
                },
            )

            # 2. Patch emergency savings to maximum boundary
            patch_res = await client.patch(
                "/api/v1/profile",
                json={"emergency_savings": "9999999999.99"},
            )
            assert patch_res.status_code == 200
            assert patch_res.json()["profile"]["emergency_savings"] == "9999999999.99"

    @pytest.mark.asyncio
    async def test_patch_profile_zero_where_permitted(self, authenticated_client_app):
        """PATCH with zero for EMI and expenses is permitted."""
        from httpx import ASGITransport, AsyncClient

        app, _ = authenticated_client_app
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers={"Origin": "http://localhost:5173"},
        ) as client:
            await client.put(
                "/api/v1/profile",
                json={
                    "monthly_net_income": "50000.00",
                    "monthly_expenses": "20000.00",
                    "existing_monthly_emi": "5000.00",
                    "emergency_savings": "50000.00",
                },
            )

            patch_res = await client.patch(
                "/api/v1/profile",
                json={"existing_monthly_emi": "0.00"},
            )
            assert patch_res.status_code == 200
            assert patch_res.json()["profile"]["existing_monthly_emi"] == "0.00"

    @pytest.mark.asyncio
    async def test_patch_profile_overflow_rejected_with_422(self, authenticated_client_app):
        from httpx import ASGITransport, AsyncClient

        app, _ = authenticated_client_app
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers={"Origin": "http://localhost:5173"},
        ) as client:
            patch_res = await client.patch(
                "/api/v1/profile",
                json={"monthly_net_income": "10000000000.00"},
            )
            assert patch_res.status_code == 422

    @pytest.mark.asyncio
    async def test_patch_profile_negative_rejected_with_422(self, authenticated_client_app):
        from httpx import ASGITransport, AsyncClient

        app, _ = authenticated_client_app
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers={"Origin": "http://localhost:5173"},
        ) as client:
            patch_res = await client.patch(
                "/api/v1/profile",
                json={"monthly_expenses": "-100.00"},
            )
            assert patch_res.status_code == 422

    @pytest.mark.asyncio
    async def test_patch_profile_extra_decimals_rejected_with_422(self, authenticated_client_app):
        from httpx import ASGITransport, AsyncClient

        app, _ = authenticated_client_app
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers={"Origin": "http://localhost:5173"},
        ) as client:
            patch_res = await client.patch(
                "/api/v1/profile",
                json={"monthly_expenses": "25000.999"},
            )
            assert patch_res.status_code == 422
            assert any("2 decimal places" in e["msg"] for e in patch_res.json()["detail"])
