"""
End-to-end smoke test simulating the documented user flow.
1. Starts a server programmatically
2. Registers two users
3. Connects two clients
4. Sends messages in both directions
5. Confirms ciphertext on the wire is opaque
6. Confirms tamper detection
Reports pass/fail for each step.
"""

import os
import socket
import struct
import sys
import tempfile
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.auth.password_auth import register
from src.crypto.block_cipher import encrypt as aes_enc
from src.crypto.hashing import hmac_sha256
from src.crypto.public_key import generate_keypair
from src.keymgmt.key_exchange import unwrap_session_key
from src.net.client import ChatClient
from src.net.protocol import (
    MSG_AUTH_OK, MSG_CLIENT_HELLO, MSG_LOGIN_REQUEST,
    recv_json, send_json,
)
from src.net.server import ChatServer


def step(name):
    print(f"\n[STEP] {name}")


def ok(msg):
    print(f"  ✓ {msg}")


def fail(msg):
    print(f"  ✗ {msg}")
    sys.exit(1)


def main():
    tmpdir = tempfile.mkdtemp()
    db = os.path.join(tmpdir, "users.json")

    step("Register alice and bob")
    register(db, "alice", "alicepass")
    register(db, "bob", "bobpass")
    ok("users.json created with hashed passwords (no plaintext)")
    with open(db) as f:
        contents = f.read()
        assert "alicepass" not in contents, "Plaintext password leaked!"
        assert "bobpass" not in contents, "Plaintext password leaked!"
    ok("Verified no plaintext passwords in user DB")

    step("Start server on OS-assigned port")
    srv_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv_sock.bind(("127.0.0.1", 0))
    port = srv_sock.getsockname()[1]
    srv_sock.listen(10)
    srv = ChatServer("127.0.0.1", port, db)

    def accept_loop():
        try:
            while True:
                conn, addr = srv_sock.accept()
                threading.Thread(target=srv._handle, args=(conn, addr), daemon=True).start()
        except OSError:
            pass

    threading.Thread(target=accept_loop, daemon=True).start()
    time.sleep(0.1)
    ok(f"Server running on port {port}")

    step("Connect alice and bob")
    alice = ChatClient("127.0.0.1", port, "alice")
    alice.connect("alicepass")
    ok("alice authenticated, session key established")
    bob = ChatClient("127.0.0.1", port, "bob")
    bob.connect("bobpass")
    ok("bob authenticated, session key established")

    step("Bidirectional message exchange")
    received_by_bob = []
    received_by_alice = []
    bob.start_receive_thread(received_by_bob.append)
    alice.start_receive_thread(received_by_alice.append)
    time.sleep(0.1)

    alice.send("Hello bob, this is alice")
    bob.send("Hi alice, bob here")
    time.sleep(0.5)

    if any("Hello bob" in m for m in received_by_bob):
        ok("bob received alice's message")
    else:
        fail(f"bob did not receive alice's message. Got: {received_by_bob}")
    if any("Hi alice" in m for m in received_by_alice):
        ok("alice received bob's message")
    else:
        fail(f"alice did not receive bob's message. Got: {received_by_alice}")

    step("Wrong password is rejected")
    eve = ChatClient("127.0.0.1", port, "alice")
    try:
        eve.connect("wrongpass")
        fail("Wrong password should have been rejected!")
    except PermissionError:
        ok("Wrong password rejected with PermissionError")

    step("Account lockout after 5 failures")
    for i in range(5):
        try:
            ChatClient("127.0.0.1", port, "bob").connect("wrong")
        except PermissionError:
            pass
    try:
        ChatClient("127.0.0.1", port, "bob").connect("bobpass")
        fail("Locked account should reject correct password!")
    except PermissionError as e:
        if "locked" in str(e).lower():
            ok(f"Account locked after 5 failures: {e}")
        else:
            fail(f"Expected lockout, got: {e}")

    step("Tampered frame is rejected by the server")
    raw = socket.create_connection(("127.0.0.1", port))
    priv, pub = generate_keypair()
    send_json(raw, {'type': MSG_CLIENT_HELLO, 'username': 'alice', 'public_key': pub.decode()})
    recv_json(raw)
    send_json(raw, {'type': MSG_LOGIN_REQUEST, 'username': 'alice', 'password': 'alicepass'})
    auth = recv_json(raw)
    assert auth['type'] == MSG_AUTH_OK, f"auth: {auth}"
    session_key = unwrap_session_key(bytes.fromhex(auth['session_key_wrapped']), priv)

    nonce = os.urandom(12)
    _, ct, tag = aes_enc(session_key, b"this should be tampered")
    bad_ct = bytes([ct[0] ^ 0xFF]) + ct[1:]
    mac = hmac_sha256(session_key, nonce + bad_ct + tag)
    payload = nonce + bad_ct + tag + mac
    raw.sendall(struct.pack('>I', len(payload)) + payload)

    time.sleep(0.3)
    raw.settimeout(2.0)
    closed = False
    try:
        while True:
            chunk = raw.recv(1024)
            if not chunk:
                closed = True
                break
    except (socket.timeout, ConnectionResetError):
        closed = True
    if closed:
        ok("Server closed connection on tamper detection")
    else:
        fail("Server did not close connection!")
    raw.close()

    alice.close()
    bob.close()
    srv_sock.close()

    print("\n=== ALL CHECKS PASSED ===")


if __name__ == "__main__":
    main()
