"""
RSA-PSS signed session tokens.
Token format (JSON): {username, expiry_utc, nonce_hex}
Signature covers the canonical JSON bytes.
"""

import json
import os
import time
from src.crypto.public_key import sign, verify

_TOKEN_TTL = 3600  # seconds


def issue_token(username: str, server_private_key_pem: bytes) -> bytes:
    """Issue a signed session token. Returns JSON bytes."""
    payload = {
        'username': username,
        'expiry_utc': int(time.time()) + _TOKEN_TTL,
        'nonce': os.urandom(16).hex(),
    }
    token_bytes = json.dumps(payload, sort_keys=True).encode()
    signature = sign(server_private_key_pem, token_bytes)
    envelope = {
        'token': token_bytes.decode(),
        'sig': signature.hex(),
    }
    return json.dumps(envelope).encode()


def verify_token(token_envelope: bytes, server_public_key_pem: bytes) -> str:
    """
    Verify a session token's signature and expiry.
    Returns the username on success.
    Raises ValueError on invalid/expired token.
    """
    envelope = json.loads(token_envelope.decode())
    token_bytes = envelope['token'].encode()
    signature = bytes.fromhex(envelope['sig'])

    if not verify(server_public_key_pem, token_bytes, signature):
        raise ValueError("Invalid token signature")

    payload = json.loads(token_bytes)
    if int(time.time()) > payload['expiry_utc']:
        raise ValueError("Token expired")

    return payload['username']
