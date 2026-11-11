"""
tests/test_auth_service.py
───────────────────────────
Integration-level tests for auth_service functions.
Uses an in-memory SQLite DB (via conftest.py fixtures) — no live Postgres needed.
"""

import hashlib
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import Session
from app.services.auth_service import (
    get_user_from_token,
    login_user,
    logout_user,
    register_user,
)
from app.utils.security import hash_session_token


# ── Helpers ───────────────────────────────────────────────────────────────────

VALID_EMAIL = "alice@example.com"
VALID_NAME = "Alice Smith"
VALID_PASSWORD = "Secure1Pass"


async def _create_alice(db: AsyncSession):
    """Register a standard test user and return the User object."""
    return await register_user(
        db=db,
        email=VALID_EMAIL,
        full_name=VALID_NAME,
        plain_password=VALID_PASSWORD,
    )


# ── Registration tests ────────────────────────────────────────────────────────

class TestRegisterUser:
    async def test_register_success(self, db: AsyncSession):
        user = await _create_alice(db)
        assert user.id is not None
        assert user.email == VALID_EMAIL
        assert user.full_name == VALID_NAME
        assert user.is_active is True

    async def test_password_is_hashed(self, db: AsyncSession):
        user = await _create_alice(db)
        assert user.hashed_password != VALID_PASSWORD
        assert user.hashed_password.startswith("$2b$")

    async def test_email_normalized_to_lowercase(self, db: AsyncSession):
        user = await register_user(
            db=db,
            email="BOB@EXAMPLE.COM",
            full_name="Bob",
            plain_password="Secure1Pass",
        )
        assert user.email == "bob@example.com"

    async def test_duplicate_email_raises(self, db: AsyncSession):
        await _create_alice(db)
        with pytest.raises(ValueError, match="already exists"):
            await register_user(
                db=db,
                email=VALID_EMAIL,
                full_name="Alice Clone",
                plain_password=VALID_PASSWORD,
            )

    async def test_duplicate_email_case_insensitive(self, db: AsyncSession):
        await _create_alice(db)
        with pytest.raises(ValueError):
            await register_user(
                db=db,
                email=VALID_EMAIL.upper(),
                full_name="Alice Upper",
                plain_password=VALID_PASSWORD,
            )

    async def test_register_exactly_72_bytes_password_success(self, db: AsyncSession):
        """SEC-VULN-007: Registering with exactly 72 UTF-8 bytes succeeds."""
        pwd_72 = "A" * 70 + "1!"  # Exactly 72 bytes
        user = await register_user(
            db=db,
            email="user72@example.com",
            full_name="User 72",
            plain_password=pwd_72,
        )
        assert user.id is not None
        assert user.email == "user72@example.com"

    async def test_register_over_72_bytes_password_raises(self, db: AsyncSession):
        """SEC-VULN-007: Direct register_user call with > 72 bytes raises ValueError."""
        pwd_73 = "A" * 71 + "1!"  # 73 bytes
        with pytest.raises(ValueError, match="72 UTF-8 bytes"):
            await register_user(
                db=db,
                email="user73@example.com",
                full_name="User 73",
                plain_password=pwd_73,
            )


# ── Login tests ───────────────────────────────────────────────────────────────

class TestLoginUser:
    async def test_login_success_returns_user_and_token(self, db: AsyncSession):
        await _create_alice(db)
        user, token = await login_user(db=db, email=VALID_EMAIL, plain_password=VALID_PASSWORD)
        assert user.email == VALID_EMAIL
        assert isinstance(token, str)
        assert len(token) > 20

    async def test_wrong_password_raises(self, db: AsyncSession):
        await _create_alice(db)
        with pytest.raises(ValueError, match="Invalid email or password"):
            await login_user(db=db, email=VALID_EMAIL, plain_password="WrongPass1")

    async def test_nonexistent_email_raises(self, db: AsyncSession):
        with pytest.raises(ValueError, match="Invalid email or password"):
            await login_user(db=db, email="ghost@example.com", plain_password="Secure1Pass")

    async def test_login_is_case_insensitive_on_email(self, db: AsyncSession):
        await _create_alice(db)
        user, token = await login_user(
            db=db,
            email=VALID_EMAIL.upper(),
            plain_password=VALID_PASSWORD,
        )
        assert user.email == VALID_EMAIL

    async def test_each_login_produces_unique_token(self, db: AsyncSession):
        await _create_alice(db)
        _, token1 = await login_user(db=db, email=VALID_EMAIL, plain_password=VALID_PASSWORD)
        _, token2 = await login_user(db=db, email=VALID_EMAIL, plain_password=VALID_PASSWORD)
        assert token1 != token2

    async def test_login_with_72_byte_password_success(self, db: AsyncSession):
        """SEC-VULN-007: Valid 72 UTF-8 byte password logs in successfully."""
        pwd_72 = "A" * 70 + "1!"
        await register_user(
            db=db,
            email="login72@example.com",
            full_name="Login 72",
            plain_password=pwd_72,
        )
        user, token = await login_user(db=db, email="login72@example.com", plain_password=pwd_72)
        assert user.email == "login72@example.com"
        assert token is not None

    async def test_login_with_multibyte_unicode_password_success(self, db: AsyncSession):
        """SEC-VULN-007: Multibyte Unicode password (72 bytes) registers and logs in."""
        unicode_pwd = "₹" * 23 + "A1!"  # 23*3 + 3 = 72 bytes
        await register_user(
            db=db,
            email="unicode@example.com",
            full_name="Unicode User",
            plain_password=unicode_pwd,
        )
        user, token = await login_user(db=db, email="unicode@example.com", plain_password=unicode_pwd)
        assert user.email == "unicode@example.com"
        assert token is not None

    async def test_login_with_oversized_truncated_equivalent_fails(self, db: AsyncSession):
        """
        SEC-VULN-007: Bcrypt truncation attack prevention.
        Victim has a 72-byte password. Attacker tries victim password + 'extra' (77 bytes).
        Direct service call MUST reject without silently accepting the truncated prefix.
        """
        victim_pwd = "V" * 70 + "9!"  # 72 bytes
        await register_user(
            db=db,
            email="victim_trunc@example.com",
            full_name="Victim Trunc",
            plain_password=victim_pwd,
        )
        # Direct call with appended characters
        attack_pwd = victim_pwd + "extra"
        with pytest.raises(ValueError, match="Invalid email or password"):
            await login_user(db=db, email="victim_trunc@example.com", plain_password=attack_pwd)


# ── Session / token tests ─────────────────────────────────────────────────────

class TestSessionManagement:
    async def test_valid_token_resolves_to_user(self, db: AsyncSession):
        await _create_alice(db)
        user, token = await login_user(db=db, email=VALID_EMAIL, plain_password=VALID_PASSWORD)
        resolved = await get_user_from_token(db=db, token=token)
        assert resolved is not None
        assert resolved.id == user.id

    async def test_raw_token_never_stored_and_sha256_hash_persisted(self, db: AsyncSession):
        """SEC-VULN-002: Verify raw token is never written to DB; only SHA-256 is stored."""
        user = await _create_alice(db)
        _, raw_token = await login_user(db=db, email=VALID_EMAIL, plain_password=VALID_PASSWORD)

        # Inspect database row directly
        res = await db.execute(select(Session).where(Session.user_id == user.id))
        stored_sessions = res.scalars().all()
        assert len(stored_sessions) >= 1

        expected_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        matching = [s for s in stored_sessions if s.token_hash == expected_hash]
        assert len(matching) == 1, "Expected exactly one session with the calculated SHA-256 hash"

        session_record = matching[0]
        # Raw token must NEVER equal stored token_hash
        assert session_record.token_hash != raw_token
        # Plaintext token attribute must not even exist on Session model
        assert not hasattr(session_record, "token") or "token" not in Session.__table__.columns
        assert len(session_record.token_hash) == 64

    async def test_invalid_token_returns_none(self, db: AsyncSession):
        result = await get_user_from_token(db=db, token="totally_fake_token")
        assert result is None

    async def test_empty_token_returns_none(self, db: AsyncSession):
        result = await get_user_from_token(db=db, token="")
        assert result is None

    async def test_expired_session_is_rejected(self, db: AsyncSession):
        """Expired sessions must not authenticate."""
        user = await _create_alice(db)
        _, raw_token = await login_user(db=db, email=VALID_EMAIL, plain_password=VALID_PASSWORD)

        # Manually backdate the session expiration to 1 hour in the past
        token_hash = hash_session_token(raw_token)
        res = await db.execute(select(Session).where(Session.token_hash == token_hash))
        session_record = res.scalar_one()
        session_record.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        await db.flush()

        # Looking up with raw token should now fail because it is expired
        resolved = await get_user_from_token(db=db, token=raw_token)
        assert resolved is None


# ── Logout tests ──────────────────────────────────────────────────────────────

class TestLogoutUser:
    async def test_logout_invalidates_token(self, db: AsyncSession):
        await _create_alice(db)
        _, token = await login_user(db=db, email=VALID_EMAIL, plain_password=VALID_PASSWORD)

        # Confirm it works before logout
        user_before = await get_user_from_token(db=db, token=token)
        assert user_before is not None

        await logout_user(db=db, token=token)

        # Token should no longer resolve to a user
        user_after = await get_user_from_token(db=db, token=token)
        assert user_after is None

    async def test_logout_deletes_only_targeted_session(self, db: AsyncSession):
        """Logging out user A must delete user A's session while user B remains logged in."""
        user_a = await _create_alice(db)
        user_b = await register_user(
            db=db,
            email="bob_sessions@example.com",
            full_name="Bob Session",
            plain_password="SecurePass123!",
        )

        _, token_a = await login_user(db=db, email=VALID_EMAIL, plain_password=VALID_PASSWORD)
        _, token_b = await login_user(db=db, email="bob_sessions@example.com", plain_password="SecurePass123!")

        # Both authenticate
        assert (await get_user_from_token(db=db, token=token_a)).id == user_a.id
        assert (await get_user_from_token(db=db, token=token_b)).id == user_b.id

        # Logout user A
        await logout_user(db=db, token=token_a)

        # User A is logged out; User B is still logged in
        assert await get_user_from_token(db=db, token=token_a) is None
        resolved_b = await get_user_from_token(db=db, token=token_b)
        assert resolved_b is not None
        assert resolved_b.id == user_b.id

    async def test_logout_nonexistent_token_does_not_raise(self, db: AsyncSession):
        """Logging out with a fake token should be a no-op."""
        await logout_user(db=db, token="nonexistent_token_xyz")


# ── Schema validation tests ───────────────────────────────────────────────────

class TestRegisterSchema:
    def test_password_requires_uppercase(self):
        from pydantic import ValidationError
        from app.schemas.auth import RegisterRequest

        with pytest.raises(ValidationError, match="uppercase"):
            RegisterRequest(
                full_name="Test User",
                email="test@example.com",
                password="alllowercase1",
            )

    def test_password_requires_digit(self):
        from pydantic import ValidationError
        from app.schemas.auth import RegisterRequest

        with pytest.raises(ValidationError, match="digit"):
            RegisterRequest(
                full_name="Test User",
                email="test@example.com",
                password="NoDigitsHere",
            )

    def test_password_too_short(self):
        from pydantic import ValidationError
        from app.schemas.auth import RegisterRequest

        with pytest.raises(ValidationError):
            RegisterRequest(
                full_name="Test User",
                email="test@example.com",
                password="Ab1",
            )

    def test_invalid_email_format(self):
        from pydantic import ValidationError
        from app.schemas.auth import RegisterRequest

        with pytest.raises(ValidationError):
            RegisterRequest(
                full_name="Test User",
                email="not-an-email",
                password="ValidPass1",
            )

    def test_blank_full_name_raises(self):
        from pydantic import ValidationError
        from app.schemas.auth import RegisterRequest

        with pytest.raises(ValidationError):
            RegisterRequest(
                full_name="   ",
                email="test@example.com",
                password="ValidPass1",
            )

    # ── SEC-VULN-007: Schema 72-Byte Validation Tests ─────────────────────────

    def test_register_schema_accepts_exactly_72_bytes_ascii(self):
        from app.schemas.auth import RegisterRequest
        pwd = "A" * 70 + "1!"  # 72 bytes
        req = RegisterRequest(
            full_name="Test User",
            email="test@example.com",
            password=pwd,
        )
        assert req.password == pwd

    def test_register_schema_accepts_multibyte_unicode_72_bytes(self):
        from app.schemas.auth import RegisterRequest
        pwd = "₹" * 23 + "A1!"  # 23*3 + 3 = 72 bytes
        req = RegisterRequest(
            full_name="Test User",
            email="test@example.com",
            password=pwd,
        )
        assert req.password == pwd

    def test_register_schema_rejects_more_than_72_bytes_ascii(self):
        from pydantic import ValidationError
        from app.schemas.auth import RegisterRequest

        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(
                full_name="Test User",
                email="test@example.com",
                password="A" * 71 + "1!",  # 73 bytes
            )
        assert "72" in str(exc_info.value)

    def test_register_schema_rejects_more_than_72_bytes_unicode(self):
        """19 fire emojis = 76 UTF-8 bytes, well under character limit but over byte limit."""
        from pydantic import ValidationError
        from app.schemas.auth import RegisterRequest

        with pytest.raises(ValidationError, match="72 UTF-8 bytes"):
            RegisterRequest(
                full_name="Test User",
                email="test@example.com",
                password="🔥" * 19 + "A1",
            )

    def test_login_schema_accepts_valid_and_72_byte_passwords(self):
        from app.schemas.auth import LoginRequest

        req1 = LoginRequest(email="u@example.com", password="NormalPassword1!")
        assert req1.password == "NormalPassword1!"

        req2 = LoginRequest(email="u@example.com", password="A" * 70 + "1!")
        assert req2.password == "A" * 70 + "1!"

    def test_login_schema_rejects_over_72_bytes_ascii(self):
        from pydantic import ValidationError
        from app.schemas.auth import LoginRequest

        with pytest.raises(ValidationError):
            LoginRequest(email="u@example.com", password="A" * 71 + "1!")

    def test_login_schema_rejects_over_72_bytes_unicode(self):
        from pydantic import ValidationError
        from app.schemas.auth import LoginRequest

        with pytest.raises(ValidationError, match="72 UTF-8 bytes"):
            LoginRequest(email="u@example.com", password="🔥" * 19)


# ── HTTP Boundary Tests for Password Truncation (SEC-VULN-007) ─────────────────


class TestAuthHTTPPasswordTruncation:
    @pytest.mark.asyncio
    async def test_register_endpoint_rejects_oversized_password_with_422(self):
        """HTTP POST /api/v1/auth/register returns 422 with clear Pydantic validation error."""
        from app.main import create_app
        from httpx import ASGITransport, AsyncClient

        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers={"Origin": "http://localhost:5173"},
        ) as client:
            res = await client.post(
                "/api/v1/auth/register",
                json={
                    "full_name": "Oversized User",
                    "email": "oversized@example.com",
                    "password": "A" * 71 + "1!",  # 73 bytes
                },
            )
            assert res.status_code == 422
            detail = res.json()["detail"]
            assert any("72" in d.get("msg", "") for d in detail)

    @pytest.mark.asyncio
    async def test_login_endpoint_rejects_oversized_password_safely(self):
        """HTTP POST /api/v1/auth/login rejects passwords exceeding 72 bytes safely."""
        from app.main import create_app
        from httpx import ASGITransport, AsyncClient

        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers={"Origin": "http://localhost:5173"},
        ) as client:
            res = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": "oversized_login@example.com",
                    "password": "🔥" * 19,  # 76 bytes
                },
            )
            assert res.status_code == 422
            detail = res.json()["detail"]
            assert any("72" in d.get("msg", "") for d in detail)

    @pytest.mark.asyncio
    async def test_http_register_and_login_with_72_byte_unicode_password(self, db: AsyncSession):
        """Complete HTTP registration and login flow with exactly 72 UTF-8 bytes Unicode password."""
        from app.database import get_db
        from app.main import create_app
        from httpx import ASGITransport, AsyncClient

        app = create_app()

        async def override_db():
            yield db

        app.dependency_overrides[get_db] = override_db

        pwd_72 = "₹" * 23 + "A1!"  # 72 bytes

        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers={"Origin": "http://localhost:5173"},
        ) as client:
            # 1. Register with 72-byte password
            reg_res = await client.post(
                "/api/v1/auth/register",
                json={
                    "full_name": "Rupee User",
                    "email": "rupee@example.com",
                    "password": pwd_72,
                },
            )
            assert reg_res.status_code == 201
            assert reg_res.json()["user"]["email"] == "rupee@example.com"

            # 2. Login with 72-byte password
            login_res = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": "rupee@example.com",
                    "password": pwd_72,
                },
            )
            assert login_res.status_code == 200
            assert login_res.json()["user"]["email"] == "rupee@example.com"
