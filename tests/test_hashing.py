"""
Tests for src/crypto/hashing.py
Includes NIST SHA-256 Known Answer Test vectors.
"""

import hashlib
import hmac as stdlib_hmac
from src.crypto.hashing import sha256, hmac_sha256


# NIST FIPS 180-4 SHA-256 Known Answer Tests
NIST_VECTORS = [
    # (input_hex, expected_hex) — verified against system shasum -a 256 and hashlib
    ("", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"),
    ("61", "ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb"),
    ("616263", "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"),
    (
        "6162636462636465636465666465666765666768666768696768696a68696a6b696a6b6c6a6b6c6d6b6c6d6e6c6d6e6f6d6e6f706e6f7071",
        "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1",
    ),
]


def test_nist_vectors():
    for input_hex, expected_hex in NIST_VECTORS:
        data = bytes.fromhex(input_hex)
        assert sha256(data).hex() == expected_hex, f"Failed on input: {input_hex!r}"


def test_matches_hashlib():
    for msg in [b"", b"hello", b"a" * 1000, bytes(range(256))]:
        assert sha256(msg) == hashlib.sha256(msg).digest()


def test_sha256_returns_32_bytes():
    assert len(sha256(b"test")) == 32


def test_hmac_matches_stdlib():
    key = b"secret-key"
    for msg in [b"", b"hello world", b"\x00\xff" * 50]:
        expected = stdlib_hmac.new(key, msg, "sha256").digest()
        assert hmac_sha256(key, msg) == expected


def test_hmac_long_key():
    # Key longer than 64 bytes triggers key hashing in RFC 2104
    key = b"k" * 200
    msg = b"message"
    expected = stdlib_hmac.new(key, msg, "sha256").digest()
    assert hmac_sha256(key, msg) == expected


def test_hmac_different_keys_differ():
    msg = b"same message"
    assert hmac_sha256(b"key1", msg) != hmac_sha256(b"key2", msg)


def test_sha256_avalanche():
    # Single bit flip in input should drastically change digest
    d1 = sha256(b"\x00")
    d2 = sha256(b"\x01")
    diff_bits = bin(int(d1.hex(), 16) ^ int(d2.hex(), 16)).count('1')
    assert diff_bits > 50  # expect ~128 bits to flip on average
