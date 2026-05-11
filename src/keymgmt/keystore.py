"""
Encrypted-at-rest key storage.
Keys are stored in a JSON file encrypted with AES-256-GCM.
The master encryption key is derived from the user's password via PBKDF2.
"""

from src.crypto.kdf import pbkdf2
import json
import os
from src.crypto.block_cipher import encrypt, decrypt

_ITERATIONS = 2_000
_KEY_LEN = 32
_SALT_LEN = 16


def _derive_master_key(password: bytes, salt: bytes) -> bytes:
    return pbkdf2(password, salt, _ITERATIONS, _KEY_LEN)


def _load_raw(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, 'rb') as f:
        return json.loads(f.read().decode())


def _save_raw(path: str, data: dict) -> None:
    with open(path, 'wb') as f:
        f.write(json.dumps(data).encode())


def init_keystore(path: str, password: bytes) -> None:
    """Create a new empty keystore protected by password."""
    if os.path.exists(path):
        raise FileExistsError(f"Keystore already exists: {path}")
    salt = os.urandom(_SALT_LEN)
    master_key = _derive_master_key(password, salt)
    # Encrypt an empty payload to verify password on future loads
    nonce, ct, tag = encrypt(master_key, b'{}')
    data = {
        '_salt': salt.hex(),
        '_nonce': nonce.hex(),
        '_tag': tag.hex(),
        '_meta': ct.hex(),
        'keys': {},
    }
    _save_raw(path, data)


def _open_keystore(path: str, password: bytes) -> tuple[dict, bytes]:
    """Load and authenticate the keystore. Returns (data_dict, master_key)."""
    data = _load_raw(path)
    if not data:
        raise FileNotFoundError(f"Keystore not found: {path}")
    salt = bytes.fromhex(data['_salt'])
    master_key = _derive_master_key(password, salt)
    # Verify password by decrypting the meta blob
    nonce = bytes.fromhex(data['_nonce'])
    tag = bytes.fromhex(data['_tag'])
    ct = bytes.fromhex(data['_meta'])
    try:
        decrypt(master_key, nonce, ct, tag)
    except ValueError:
        raise ValueError("Wrong keystore password")
    return data, master_key


def save_key(path: str, password: bytes, name: str, key_bytes: bytes) -> None:
    """Encrypt and store a key under *name* in the keystore."""
    data, master_key = _open_keystore(path, password)
    nonce, ct, tag = encrypt(master_key, key_bytes)
    data['keys'][name] = {
        'nonce': nonce.hex(),
        'ct': ct.hex(),
        'tag': tag.hex(),
    }
    _save_raw(path, data)


def load_key(path: str, password: bytes, name: str) -> bytes:
    """Load and decrypt a key by *name*. Raises KeyError if not found."""
    data, master_key = _open_keystore(path, password)
    if name not in data['keys']:
        raise KeyError(f"Key not found in keystore: {name}")
    entry = data['keys'][name]
    return decrypt(
        master_key,
        bytes.fromhex(entry['nonce']),
        bytes.fromhex(entry['ct']),
        bytes.fromhex(entry['tag']),
    )


def list_keys(path: str, password: bytes) -> list[str]:
    """Return names of all keys in the keystore."""
    data, _ = _open_keystore(path, password)
    return list(data['keys'].keys())


def delete_key(path: str, password: bytes, name: str) -> None:
    """Remove a key from the keystore."""
    data, _ = _open_keystore(path, password)
    if name not in data['keys']:
        raise KeyError(f"Key not found: {name}")
    del data['keys'][name]
    _save_raw(path, data)
