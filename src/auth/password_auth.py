"""
Password-based user authentication.
Stores (username, salt, PBKDF2-hash) in a JSON file.
Uses constant-time comparison to prevent timing attacks.
"""

from src.crypto.kdf import pbkdf2
import hmac as _hmac_stdlib
import json
import os

_ITERATIONS = 2_000
_SALT_LEN = 16
_HASH_LEN = 32
_MAX_FAILURES = 5


def _load_db(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, 'r') as f:
        return json.load(f)


def _save_db(path: str, db: dict) -> None:
    with open(path, 'w') as f:
        json.dump(db, f)


def register(db_path: str, username: str, password: str) -> None:
    """Register a new user. Raises ValueError if username already exists."""
    db = _load_db(db_path)
    if username in db:
        raise ValueError(f"Username already exists: {username}")
    salt = os.urandom(_SALT_LEN)
    pw_hash = pbkdf2(password.encode(), salt, _ITERATIONS, _HASH_LEN)
    db[username] = {
        'salt': salt.hex(),
        'hash': pw_hash.hex(),
        'failures': 0,
        'locked': False,
    }
    _save_db(db_path, db)


def login(db_path: str, username: str, password: str) -> bool:
    """
    Authenticate a user. Returns True on success.
    Raises ValueError on locked account.
    Returns False on wrong password (increments failure counter).
    """
    db = _load_db(db_path)
    if username not in db:
        return False
    entry = db[username]
    if entry.get('locked'):
        raise ValueError(f"Account locked after {_MAX_FAILURES} failed attempts")

    salt = bytes.fromhex(entry['salt'])
    stored_hash = bytes.fromhex(entry['hash'])
    candidate = pbkdf2(password.encode(), salt, _ITERATIONS, _HASH_LEN)

    # Constant-time comparison
    if _hmac_stdlib.compare_digest(candidate, stored_hash):
        entry['failures'] = 0
        _save_db(db_path, db)
        return True

    entry['failures'] = entry.get('failures', 0) + 1
    if entry['failures'] >= _MAX_FAILURES:
        entry['locked'] = True
    _save_db(db_path, db)
    return False


def unlock(db_path: str, username: str) -> None:
    """Admin operation: reset failure counter and unlock an account."""
    db = _load_db(db_path)
    if username not in db:
        raise KeyError(f"Unknown user: {username}")
    db[username]['failures'] = 0
    db[username]['locked'] = False
    _save_db(db_path, db)


def user_exists(db_path: str, username: str) -> bool:
    return username in _load_db(db_path)
