"""
Wire protocol for the secure chat.

Frame format (after the handshake):
  [4B len][12B nonce][N bytes ciphertext][16B GCM tag][32B HMAC]

Handshake message types are plain JSON (sent before the session key is
established). Post-handshake messages use the binary frame format.
"""

import json
import socket
import struct

from src.crypto.block_cipher import encrypt as aes_encrypt, decrypt as aes_decrypt
from src.crypto.hashing import hmac_sha256

# Handshake message type tags
MSG_CLIENT_HELLO = "CLIENT_HELLO"
MSG_SERVER_HELLO = "SERVER_HELLO"
MSG_LOGIN_REQUEST = "LOGIN_REQUEST"
MSG_AUTH_OK = "AUTH_OK"
MSG_AUTH_FAIL = "AUTH_FAIL"
MSG_REGISTER_REQUEST = "REGISTER_REQUEST"
MSG_REGISTER_OK = "REGISTER_OK"
MSG_REGISTER_FAIL = "REGISTER_FAIL"
MSG_CHAT = "CHAT"
MSG_ERROR = "ERROR"

# Nonce cache: a simple set is sufficient per-connection (not global)


def send_json(sock: socket.socket, obj: dict) -> None:
    """Send a JSON object framed with a 4-byte length prefix."""
    data = json.dumps(obj).encode()
    sock.sendall(struct.pack('>I', len(data)) + data)


def recv_json(sock: socket.socket) -> dict:
    """Receive a length-prefixed JSON object."""
    raw_len = _recv_exact(sock, 4)
    length = struct.unpack('>I', raw_len)[0]
    data = _recv_exact(sock, length)
    return json.loads(data.decode())


def send_frame(sock: socket.socket, session_key: bytes, plaintext: bytes) -> None:
    """Encrypt plaintext and send as a binary frame."""
    nonce, ct, tag = aes_encrypt(session_key, plaintext)
    mac = hmac_sha256(session_key, nonce + ct + tag)
    payload = nonce + ct + tag + mac
    sock.sendall(struct.pack('>I', len(payload)) + payload)


def recv_frame(sock: socket.socket, session_key: bytes, seen_nonces: set) -> bytes:
    """
    Receive and authenticate a binary frame.
    Raises ValueError on tamper, replay, or MAC failure.
    Returns decrypted plaintext.
    """
    raw_len = _recv_exact(sock, 4)
    length = struct.unpack('>I', raw_len)[0]
    payload = _recv_exact(sock, length)

    nonce = payload[:12]
    ct = payload[12:length - 48]
    tag = payload[length - 48:length - 32]
    mac = payload[length - 32:]

    # Replay check
    if nonce in seen_nonces:
        raise ValueError("Replay detected: duplicate nonce")
    # MAC check
    expected_mac = hmac_sha256(session_key, nonce + ct + tag)
    import hmac as _hmac
    if not _hmac.compare_digest(mac, expected_mac):
        raise ValueError("HMAC verification failed")

    seen_nonces.add(nonce)
    return aes_decrypt(session_key, nonce, ct, tag)


def _recv_exact(sock: socket.socket, n: int) -> bytes:
    """Read exactly *n* bytes from the socket."""
    buf = b''
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("Connection closed unexpectedly")
        buf += chunk
    return buf
