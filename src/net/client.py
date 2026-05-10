"""
TCP chat client.
Connects to the server, completes the handshake, then enters a chat REPL.
"""

import socket
import threading

from src.auth.session import verify_token
from src.crypto.public_key import generate_keypair
from src.keymgmt.key_exchange import unwrap_session_key
from src.net.protocol import (
    MSG_AUTH_FAIL, MSG_AUTH_OK, MSG_CLIENT_HELLO,
    MSG_LOGIN_REQUEST, MSG_REGISTER_FAIL, MSG_REGISTER_OK,
    MSG_REGISTER_REQUEST, MSG_SERVER_HELLO,
    recv_frame, recv_json, send_frame, send_json,
)


def register_remote(host: str, port: int, username: str, password: str) -> None:
    """Register a new user on the server. Raises ValueError on failure."""
    import socket
    from src.crypto.public_key import generate_keypair
    _, pub = generate_keypair()
    sock = socket.create_connection((host, port))
    try:
        send_json(sock, {
            'type': MSG_CLIENT_HELLO,
            'username': username,
            'public_key': pub.decode(),
        })
        recv_json(sock)  # ServerHello (ignored for registration)
        send_json(sock, {
            'type': MSG_REGISTER_REQUEST,
            'username': username,
            'password': password,
        })
        resp = recv_json(sock)
        if resp.get('type') == MSG_REGISTER_OK:
            return
        raise ValueError(resp.get('msg', 'Registration failed'))
    finally:
        sock.close()


class ChatClient:
    def __init__(self, host: str, port: int, username: str):
        self._host = host
        self._port = port
        self._username = username
        self._priv, self._pub = generate_keypair()
        self._session_key: bytes | None = None
        self._server_pub: bytes | None = None
        self._sock: socket.socket | None = None
        self._seen_nonces: set = set()

    def connect(self, password: str) -> None:
        """Connect and complete the handshake. Raises on failure."""
        self._sock = socket.create_connection((self._host, self._port))

        send_json(self._sock, {
            'type': MSG_CLIENT_HELLO,
            'username': self._username,
            'public_key': self._pub.decode(),
        })

        hello = recv_json(self._sock)
        if hello.get('type') != MSG_SERVER_HELLO:
            raise ConnectionError(f"Unexpected server response: {hello}")
        self._server_pub = hello['public_key'].encode()

        send_json(self._sock, {
            'type': MSG_LOGIN_REQUEST,
            'username': self._username,
            'password': password,
        })

        auth = recv_json(self._sock)
        if auth.get('type') == MSG_AUTH_FAIL:
            raise PermissionError(f"Authentication failed: {auth.get('msg')}")
        if auth.get('type') != MSG_AUTH_OK:
            raise ConnectionError(f"Unexpected auth response: {auth}")

        token = auth['token'].encode()
        verify_token(token, self._server_pub)  # raises if invalid
        self._session_key = unwrap_session_key(
            bytes.fromhex(auth['session_key_wrapped']),
            self._priv,
        )
        print(f"[{self._username}] Connected. Type messages, Ctrl-C to quit.")

    def start_receive_thread(self, on_message) -> threading.Thread:
        """Start a background thread that calls *on_message(text)* for each received frame."""
        def _recv_loop():
            try:
                while True:
                    data = recv_frame(self._sock, self._session_key, self._seen_nonces)
                    on_message(data.decode(errors='replace'))
            except (ConnectionError, OSError, ValueError):
                pass
        t = threading.Thread(target=_recv_loop, daemon=True)
        t.start()
        return t

    def send(self, message: str) -> None:
        if self._session_key is None or self._sock is None:
            raise RuntimeError("Not connected")
        send_frame(self._sock, self._session_key, message.encode())

    def close(self) -> None:
        if self._sock:
            self._sock.close()
            self._sock = None
