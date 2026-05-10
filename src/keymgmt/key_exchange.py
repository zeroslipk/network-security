"""
RSA-OAEP session key wrapping for secure key transport.
"""

import os
from src.crypto.public_key import encrypt, decrypt


def generate_session_key() -> bytes:
    """Generate a fresh 256-bit AES session key."""
    return os.urandom(32)


def wrap_session_key(session_key: bytes, recipient_public_key_pem: bytes) -> bytes:
    """Wrap *session_key* with recipient's RSA public key (OAEP)."""
    return encrypt(recipient_public_key_pem, session_key)


def unwrap_session_key(wrapped_key: bytes, private_key_pem: bytes) -> bytes:
    """Unwrap an RSA-OAEP wrapped session key using the private key."""
    return decrypt(private_key_pem, wrapped_key)
