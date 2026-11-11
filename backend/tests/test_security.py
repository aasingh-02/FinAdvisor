"""
tests/test_security.py
───────────────────────
Unit tests for password hashing and session token generation.
These are pure-function tests — no DB required.
"""

import hashlib
import pytest
from app.utils.security import (
    generate_session_token,
    hash_password,
    hash_session_token,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_is_not_plain_text(self):
        plain = "MyPassword1"
        hashed = hash_password(plain)
        assert hashed != plain

    def test_hash_starts_with_bcrypt_prefix(self):
        hashed = hash_password("MyPassword1")
        assert hashed.startswith("$2b$")

    def test_correct_password_verifies(self):
        plain = "Correct!Password9"
        hashed = hash_password(plain)
        assert verify_password(plain, hashed) is True

    def test_wrong_password_fails(self):
        hashed = hash_password("MyPassword1")
        assert verify_password("WrongPassword1", hashed) is False

    def test_empty_string_does_not_verify(self):
        hashed = hash_password("MyPassword1")
        assert verify_password("", hashed) is False

    def test_different_hashes_for_same_password(self):
        """bcrypt salts ensure each hash is unique."""
        plain = "MyPassword1"
        hash1 = hash_password(plain)
        hash2 = hash_password(plain)
        assert hash1 != hash2

    def test_both_hashes_still_verify(self):
        plain = "MyPassword1"
        hash1 = hash_password(plain)
        hash2 = hash_password(plain)
        assert verify_password(plain, hash1) is True
        assert verify_password(plain, hash2) is True

    # ── SEC-VULN-007: Bcrypt 72-Byte Truncation Tests ─────────────────────────

    def test_password_exactly_72_bytes_ascii_hashes_and_verifies(self):
        """A password of exactly 72 ASCII bytes (72 chars) must hash and verify correctly."""
        plain = "A" * 70 + "1!"  # 70 + 2 = 72 bytes
        assert len(plain.encode("utf-8")) == 72
        hashed = hash_password(plain)
        assert verify_password(plain, hashed) is True

    def test_password_over_72_bytes_ascii_raises_in_hash_password(self):
        """hash_password must reject passwords exceeding 72 UTF-8 bytes."""
        oversized = "A" * 71 + "1!"  # 71 + 2 = 73 bytes
        assert len(oversized.encode("utf-8")) == 73
        with pytest.raises(ValueError, match="72 UTF-8 bytes"):
            hash_password(oversized)

    def test_password_over_72_bytes_rejected_in_verify_password(self):
        """verify_password must immediately return False for passwords > 72 bytes."""
        valid_72 = "A" * 70 + "1!"
        hashed = hash_password(valid_72)

        oversized = valid_72 + "extra"  # 77 bytes
        assert len(oversized.encode("utf-8")) == 77
        assert verify_password(oversized, hashed) is False

    def test_truncation_vulnerability_prevented(self):
        """
        Critical security test: Bcrypt natively truncates at 72 bytes, meaning
        password + 'garbage' would silently verify against the hash of password.
        verify_password must reject the extended password.
        """
        base_password = "K" * 70 + "9!"  # Exactly 72 bytes
        assert len(base_password.encode("utf-8")) == 72
        hashed = hash_password(base_password)

        # Attacker appends characters to a 72-byte password
        appended_password = base_password + "AttackSuffix"
        assert verify_password(appended_password, hashed) is False

    def test_multibyte_unicode_password_exactly_72_bytes(self):
        """
        Multibyte Unicode password occupying exactly 72 UTF-8 bytes:
        23 Indian Rupee symbols (₹ = 3 bytes each -> 69 bytes) + 'A1!' (3 bytes) = 72 bytes.
        Only 26 characters, but exactly 72 UTF-8 bytes.
        """
        plain = "₹" * 23 + "A1!"
        assert len(plain) == 26
        assert len(plain.encode("utf-8")) == 72

        hashed = hash_password(plain)
        assert verify_password(plain, hashed) is True

    def test_multibyte_unicode_password_over_72_bytes_rejected(self):
        """
        Multibyte Unicode password: 24 Rupee symbols (72 bytes) + 'A1' (2 bytes) = 74 bytes.
        Even though it is only 26 characters, UTF-8 byte length is 74 -> MUST be rejected.
        """
        oversized = "₹" * 24 + "A1"
        assert len(oversized) == 26
        assert len(oversized.encode("utf-8")) == 74

        with pytest.raises(ValueError, match="72 UTF-8 bytes"):
            hash_password(oversized)

        # verify_password must return False
        assert verify_password(oversized, "$2b$12$dummyhashforverificationcheck123456789012345678901234") is False

    def test_emoji_multibyte_passwords(self):
        """
        Emojis occupy 4 UTF-8 bytes each.
        17 fire emojis (68 bytes) + 'A1!' (3 bytes) = 71 bytes (valid).
        18 fire emojis (72 bytes) + 'A' (1 byte) = 73 bytes (invalid).
        """
        valid_emoji = "🔥" * 17 + "A1!"
        assert len(valid_emoji.encode("utf-8")) == 71
        hashed = hash_password(valid_emoji)
        assert verify_password(valid_emoji, hashed) is True

        oversized_emoji = "🔥" * 18 + "A1"
        assert len(oversized_emoji.encode("utf-8")) == 74
        with pytest.raises(ValueError, match="72 UTF-8 bytes"):
            hash_password(oversized_emoji)
        assert verify_password(oversized_emoji, hashed) is False

    def test_existing_password_compatibility(self):
        """
        Verify existing known bcrypt hashes remain 100% compatible.
        """
        known_plain = "Password123!"
        known_hash = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4N2J6L4f5K"
        # Test hash_password generates valid bcrypt hash for normal passwords
        new_hash = hash_password(known_plain)
        assert verify_password(known_plain, new_hash) is True
        assert verify_password("WrongPass123!", new_hash) is False


class TestSessionTokenGeneration:
    def test_token_is_string(self):
        assert isinstance(generate_session_token(), str)

    def test_token_minimum_length(self):
        # 64 bytes base64url → at least 85 characters
        assert len(generate_session_token()) >= 85

    def test_tokens_are_unique(self):
        tokens = {generate_session_token() for _ in range(1000)}
        assert len(tokens) == 1000  # all unique

    def test_custom_byte_length(self):
        short = generate_session_token(nbytes=16)
        assert len(short) >= 20  # 16 bytes → ~22 chars base64url


class TestSessionTokenHashing:
    def test_hash_session_token_matches_sha256(self):
        token = "test_session_token_value_123"
        expected = hashlib.sha256(token.encode("utf-8")).hexdigest()
        assert hash_session_token(token) == expected

    def test_hash_session_token_length_is_64(self):
        token = generate_session_token()
        hashed = hash_session_token(token)
        assert len(hashed) == 64
        assert isinstance(hashed, str)

    def test_hash_session_token_is_deterministic(self):
        token = "fixed_token_abc_xyz"
        assert hash_session_token(token) == hash_session_token(token)

    def test_different_tokens_produce_different_hashes(self):
        token1 = generate_session_token()
        token2 = generate_session_token()
        assert hash_session_token(token1) != hash_session_token(token2)

    def test_empty_token_returns_empty_string(self):
        assert hash_session_token("") == ""
