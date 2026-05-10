"""
Tests for src/auth/password_auth.py and src/auth/session.py
"""

import pytest
from src.auth.password_auth import register, login, unlock, user_exists
from src.auth.session import issue_token, verify_token
from src.crypto.public_key import generate_keypair


@pytest.fixture
def db(tmp_path):
    return str(tmp_path / "users.json")


@pytest.fixture(scope="module")
def server_keys():
    priv, pub = generate_keypair()
    return priv, pub


def test_register_and_login(db):
    register(db, "alice", "s3cr3t!")
    assert login(db, "alice", "s3cr3t!") is True


def test_user_exists_after_register(db):
    register(db, "bob", "pass")
    assert user_exists(db, "bob") is True
    assert user_exists(db, "nobody") is False


def test_wrong_password_fails(db):
    register(db, "carol", "correct")
    assert login(db, "carol", "wrong") is False


def test_unknown_user_fails(db):
    assert login(db, "ghost", "any") is False


def test_duplicate_register_raises(db):
    register(db, "dave", "pass")
    with pytest.raises(ValueError, match="already exists"):
        register(db, "dave", "pass2")


def test_lockout_after_five_failures(db):
    register(db, "eve", "right")
    for _ in range(5):
        login(db, "eve", "wrong")
    with pytest.raises(ValueError, match="locked"):
        login(db, "eve", "right")


def test_unlock_resets_lockout(db):
    register(db, "frank", "right")
    for _ in range(5):
        login(db, "frank", "wrong")
    unlock(db, "frank")
    assert login(db, "frank", "right") is True


def test_login_resets_failure_counter(db):
    register(db, "grace", "right")
    for _ in range(4):
        login(db, "grace", "wrong")
    login(db, "grace", "right")  # success should reset counter
    # Should be able to fail 4 more times without lockout
    for _ in range(4):
        login(db, "grace", "wrong")
    assert login(db, "grace", "right") is True


# Session token tests

def test_issue_and_verify_token(server_keys):
    priv, pub = server_keys
    token = issue_token("alice", priv)
    username = verify_token(token, pub)
    assert username == "alice"


def test_tampered_token_rejected(server_keys):
    priv, pub = server_keys
    token = bytearray(issue_token("alice", priv))
    token[10] ^= 0x01
    with pytest.raises(Exception):
        verify_token(bytes(token), pub)


def test_wrong_pubkey_rejected(server_keys):
    priv, _ = server_keys
    _, wrong_pub = generate_keypair()
    token = issue_token("alice", priv)
    with pytest.raises(ValueError):
        verify_token(token, wrong_pub)
