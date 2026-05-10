"""
PBKDF2-HMAC-SHA256 implemented from scratch per RFC 8018 §5.2.
Depends only on our own hmac_sha256.
"""

import struct
from src.crypto.hashing import hmac_sha256


def pbkdf2(password: bytes, salt: bytes, iterations: int, key_len: int) -> bytes:
    """
    Derive a key of *key_len* bytes from *password* and *salt*.
    Uses HMAC-SHA256 as the pseudorandom function.
    """
    h_len = 32  # SHA-256 output length in bytes
    num_blocks = -(-key_len // h_len)  # ceiling division

    dk = b''
    for block_num in range(1, num_blocks + 1):
        # U1 = PRF(password, salt || INT(block_num))
        u = hmac_sha256(password, salt + struct.pack('>I', block_num))
        result = u
        for _ in range(iterations - 1):
            u = hmac_sha256(password, u)
            result = bytes(a ^ b for a, b in zip(result, u))
        dk += result

    return dk[:key_len]
