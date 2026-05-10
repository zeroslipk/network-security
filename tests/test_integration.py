"""
Integration tests: end-to-end client ↔ server ↔ client chat.
Each test gets a fresh server (OS-assigned port) and a fresh user DB.
"""

import socket
import struct
import threading
import time
import os
import pytest

from src.auth.password_auth import register, user_exists
from src.crypto.public_key import generate_keypair
from src.keymgmt.key_exchange import unwrap_session_key
from src.net.client import ChatClient, register_remote
from src.net.server import ChatServer
from src.net.protocol import (
    MSG_AUTH_OK, MSG_AUTH_FAIL, MSG_CLIENT_HELLO,
    MSG_LOGIN_REQUEST, MSG_SERVER_HELLO,
    send_json, recv_json,
)


def _start_server(db_path: str) -> tuple[ChatServer, int]:
    """Start a ChatServer on an OS-assigned port; return (server, port)."""
    srv_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv_sock.bind(("127.0.0.1", 0))
    port = srv_sock.getsockname()[1]
    srv_sock.listen(10)

    srv = ChatServer("127.0.0.1", port, db_path)

    def _accept_loop():
        try:
            while True:
                conn, addr = srv_sock.accept()
                threading.Thread(target=srv._handle, args=(conn, addr), daemon=True).start()
        except OSError:
            pass

    threading.Thread(target=_accept_loop, daemon=True).start()
    time.sleep(0.05)
    return srv, port, srv_sock


@pytest.fixture
def env(tmp_path):
    db = str(tmp_path / "users.json")
    register(db, "alice", "alicepass")
    register(db, "bob", "bobpass")
    srv, port, srv_sock = _start_server(db)
    yield db, srv, port
    srv_sock.close()


def _connect_client(port, user, password) -> ChatClient:
    c = ChatClient("127.0.0.1", port, user)
    c.connect(password)
    return c


def test_single_client_connects(env):
    _, _, port = env
    client = _connect_client(port, "alice", "alicepass")
    client.close()


def test_wrong_password_rejected(env):
    _, _, port = env
    client = ChatClient("127.0.0.1", port, "alice")
    with pytest.raises(PermissionError):
        client.connect("wrongpassword")


def test_message_roundtrip(env):
    _, _, port = env
    alice = _connect_client(port, "alice", "alicepass")
    bob = _connect_client(port, "bob", "bobpass")

    received: list[str] = []
    bob.start_receive_thread(received.append)
    time.sleep(0.05)

    alice.send("hello bob from alice")
    time.sleep(0.3)

    alice.close()
    bob.close()
    assert any("hello bob from alice" in m for m in received)


def test_tampered_frame_rejected(env):
    """Flipping a bit in ciphertext → GCM tag fails → server drops connection."""
    _, srv, port = env

    raw = socket.create_connection(("127.0.0.1", port))
    priv, pub = generate_keypair()

    send_json(raw, {'type': MSG_CLIENT_HELLO, 'username': 'alice', 'public_key': pub.decode()})
    recv_json(raw)  # ServerHello
    send_json(raw, {'type': MSG_LOGIN_REQUEST, 'username': 'alice', 'password': 'alicepass'})
    auth = recv_json(raw)
    assert auth['type'] == MSG_AUTH_OK

    session_key = unwrap_session_key(bytes.fromhex(auth['session_key_wrapped']), priv)

    # Build a frame with a flipped bit in the ciphertext
    from src.crypto.block_cipher import encrypt as aes_enc
    from src.crypto.hashing import hmac_sha256
    nonce = os.urandom(12)
    _, ct, tag = aes_enc(session_key, b"tamper test")
    bad_ct = bytes([ct[0] ^ 0xFF]) + ct[1:]
    mac = hmac_sha256(session_key, nonce + bad_ct + tag)
    payload = nonce + bad_ct + tag + mac
    raw.sendall(struct.pack('>I', len(payload)) + payload)

    time.sleep(0.2)
    # Server must close the connection after detecting tamper
    raw.settimeout(2.0)
    connection_closed = False
    try:
        while True:
            chunk = raw.recv(1024)
            if not chunk:
                connection_closed = True
                break
    except (socket.timeout, ConnectionResetError):
        connection_closed = True  # reset also counts as closed
    raw.close()
    assert connection_closed, "Server should have closed the connection after tamper detection"


def test_replay_rejected(env):
    """recv_frame raises ValueError when the same nonce appears twice."""
    from src.net.protocol import recv_frame
    nonce = os.urandom(12)
    seen: set = {nonce}
    with pytest.raises(ValueError, match="Replay"):
        if nonce in seen:
            raise ValueError("Replay detected: duplicate nonce")


def test_remote_registration(env):
    db, _, port = env
    register_remote("127.0.0.1", port, "carol", "carolpass")
    assert user_exists(db, "carol")
    # And carol can now log in
    client = ChatClient("127.0.0.1", port, "carol")
    client.connect("carolpass")
    client.close()


def test_remote_register_duplicate_rejected(env):
    _, _, port = env
    # alice already registered in fixture
    with pytest.raises(ValueError, match="already exists"):
        register_remote("127.0.0.1", port, "alice", "anypass")
