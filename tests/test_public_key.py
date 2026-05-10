"""
Tests for src/crypto/public_key.py (RSA-2048 OAEP/PSS).
"""

import pytest
from src.crypto.public_key import generate_keypair, encrypt, decrypt, sign, verify


@pytest.fixture(scope="module")
def keypair():
    return generate_keypair()


def test_keypair_generation(keypair):
    priv, pub = keypair
    assert b"BEGIN RSA PRIVATE KEY" in priv or b"BEGIN PRIVATE KEY" in priv
    assert b"BEGIN PUBLIC KEY" in pub or b"BEGIN RSA PUBLIC KEY" in pub


def test_encrypt_decrypt_roundtrip(keypair):
    priv, pub = keypair
    plaintext = b"session-key-32-bytes-long-data!!"
    ciphertext = encrypt(pub, plaintext)
    assert decrypt(priv, ciphertext) == plaintext


def test_ciphertext_is_not_plaintext(keypair):
    _, pub = keypair
    plaintext = b"secret"
    assert encrypt(pub, plaintext) != plaintext


def test_encrypt_nondeterministic(keypair):
    _, pub = keypair
    msg = b"same message"
    c1 = encrypt(pub, msg)
    c2 = encrypt(pub, msg)
    assert c1 != c2  # OAEP uses random padding


def test_wrong_key_decrypt_fails(keypair):
    _, pub = keypair
    priv2, _ = generate_keypair()
    ciphertext = encrypt(pub, b"data")
    with pytest.raises(Exception):
        decrypt(priv2, ciphertext)


def test_sign_verify(keypair):
    priv, pub = keypair
    message = b"authenticate this"
    sig = sign(priv, message)
    assert verify(pub, message, sig) is True


def test_tampered_message_fails_verify(keypair):
    priv, pub = keypair
    sig = sign(priv, b"original")
    assert verify(pub, b"tampered", sig) is False


def test_wrong_key_verify_fails(keypair):
    priv, _ = keypair
    _, pub2 = generate_keypair()
    sig = sign(priv, b"message")
    assert verify(pub2, b"message", sig) is False


def test_signature_nondeterministic(keypair):
    priv, _ = keypair
    msg = b"msg"
    s1 = sign(priv, msg)
    s2 = sign(priv, msg)
    assert s1 != s2  # PSS uses random salt
