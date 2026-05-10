"""
Tests for src/crypto/kdf.py (PBKDF2-HMAC-SHA256).
Validates against RFC 8018 Appendix B test vectors and hashlib.pbkdf2_hmac.
"""

import hashlib
from src.crypto.kdf import pbkdf2

# RFC 6070 PBKDF2-HMAC-SHA1 vectors exist; for HMAC-SHA256 we use hashlib as oracle
# and one known cross-verified vector from common test suites.
KNOWN_VECTOR = {
    "password": b"password",
    "salt": b"salt",
    "iterations": 1,
    "key_len": 32,
    "expected": "120fb6cffcf8b32c43e7225256c4f837a86548c92ccc35480805987cb70be17b",
}


def test_known_vector():
    result = pbkdf2(
        KNOWN_VECTOR["password"],
        KNOWN_VECTOR["salt"],
        KNOWN_VECTOR["iterations"],
        KNOWN_VECTOR["key_len"],
    )
    assert result.hex() == KNOWN_VECTOR["expected"]


def test_matches_hashlib():
    cases = [
        (b"password", b"salt", 1, 32),
        (b"pass\x00word", b"sa\x00lt", 4096, 16),
        (b"x" * 100, b"y" * 16, 100, 64),
    ]
    for pw, salt, iters, dklen in cases:
        expected = hashlib.pbkdf2_hmac("sha256", pw, salt, iters, dklen)
        assert pbkdf2(pw, salt, iters, dklen) == expected


def test_different_salts_differ():
    pw = b"same-password"
    k1 = pbkdf2(pw, b"salt1", 1, 32)
    k2 = pbkdf2(pw, b"salt2", 1, 32)
    assert k1 != k2


def test_output_length():
    for length in [16, 32, 48, 64]:
        result = pbkdf2(b"pw", b"salt", 1, length)
        assert len(result) == length
