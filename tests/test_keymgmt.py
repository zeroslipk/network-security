"""
Tests for src/keymgmt/keystore.py and src/keymgmt/key_exchange.py
"""

import os
import pytest
import tempfile
from src.keymgmt.keystore import init_keystore, save_key, load_key, list_keys, delete_key
from src.keymgmt.key_exchange import generate_session_key, wrap_session_key, unwrap_session_key
from src.crypto.public_key import generate_keypair


@pytest.fixture
def ks(tmp_path):
    path = str(tmp_path / "test.ks")
    init_keystore(path, b"password123")
    return path


def test_init_creates_file(ks):
    assert os.path.exists(ks)


def test_init_twice_raises(ks):
    with pytest.raises(FileExistsError):
        init_keystore(ks, b"password123")


def test_save_and_load_key(ks):
    key = os.urandom(32)
    save_key(ks, b"password123", "mykey", key)
    loaded = load_key(ks, b"password123", "mykey")
    assert loaded == key


def test_load_missing_key_raises(ks):
    with pytest.raises(KeyError):
        load_key(ks, b"password123", "nonexistent")


def test_wrong_password_raises(ks):
    save_key(ks, b"password123", "k", b"data")
    with pytest.raises(ValueError, match="Wrong keystore password"):
        load_key(ks, b"wrongpass", "k")


def test_list_keys(ks):
    save_key(ks, b"password123", "alpha", b"a" * 32)
    save_key(ks, b"password123", "beta", b"b" * 32)
    keys = list_keys(ks, b"password123")
    assert set(keys) == {"alpha", "beta"}


def test_delete_key(ks):
    save_key(ks, b"password123", "temp", b"x" * 16)
    delete_key(ks, b"password123", "temp")
    assert "temp" not in list_keys(ks, b"password123")


def test_delete_missing_key_raises(ks):
    with pytest.raises(KeyError):
        delete_key(ks, b"password123", "ghost")


def test_tampered_keystore_rejected(ks, tmp_path):
    save_key(ks, b"password123", "k", b"secret")
    # Corrupt the keystore file
    with open(ks, 'r+b') as f:
        data = bytearray(f.read())
        data[len(data) // 2] ^= 0xFF
        f.seek(0)
        f.write(bytes(data))
    with pytest.raises(Exception):
        load_key(ks, b"password123", "k")


# Key exchange tests

def test_session_key_length():
    assert len(generate_session_key()) == 32


def test_wrap_unwrap_roundtrip():
    priv, pub = generate_keypair()
    session_key = generate_session_key()
    wrapped = wrap_session_key(session_key, pub)
    unwrapped = unwrap_session_key(wrapped, priv)
    assert unwrapped == session_key


def test_wrap_nondeterministic():
    _, pub = generate_keypair()
    key = generate_session_key()
    assert wrap_session_key(key, pub) != wrap_session_key(key, pub)


def test_unwrap_wrong_key_fails():
    _, pub = generate_keypair()
    priv2, _ = generate_keypair()
    wrapped = wrap_session_key(generate_session_key(), pub)
    with pytest.raises(Exception):
        unwrap_session_key(wrapped, priv2)
