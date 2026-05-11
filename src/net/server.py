"""
TCP chat server.
Handles multiple clients concurrently via threads.
Each client goes through the handshake, then enters the chat loop.
"""

import socket
import threading

from src.auth.password_auth import login, register, user_exists
from src.auth.session import issue_token
from src.crypto.public_key import generate_keypair, decrypt as rsa_decrypt
from src.keymgmt.key_exchange import generate_session_key, wrap_session_key
import os
from src.net.protocol import (
    MSG_AUTH_FAIL, MSG_AUTH_OK, MSG_CLIENT_HELLO, MSG_ERROR,
    MSG_LOGIN_REQUEST, MSG_REGISTER_FAIL, MSG_REGISTER_OK,
    MSG_REGISTER_REQUEST, MSG_SERVER_HELLO,
    recv_frame, recv_json, send_frame, send_json,
)


class ChatServer:
    def __init__(self, host: str, port: int, db_path: str):
        self._host = host
        self._port = port
        self._db_path = db_path
        
        key_file = "server_key.pem"
        pub_file = "server_pub.pem"
        if os.path.exists(key_file) and os.path.exists(pub_file):
            with open(key_file, "rb") as f:
                self._server_priv = f.read()
            with open(pub_file, "rb") as f:
                self._server_pub = f.read()
        else:
            self._server_priv, self._server_pub = generate_keypair()
            with open(key_file, "wb") as f:
                f.write(self._server_priv)
            with open(pub_file, "wb") as f:
                f.write(self._server_pub)
        self._clients: dict[str, socket.socket] = {}
        self._lock = threading.Lock()

    def start(self) -> None:
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.bind((self._host, self._port))
        srv.listen(10)
        print(f"[server] Listening on {self._host}:{self._port}")
        while True:
            conn, addr = srv.accept()
            t = threading.Thread(target=self._handle, args=(conn, addr), daemon=True)
            t.start()

    def _handle(self, conn: socket.socket, addr) -> None:
        username = None
        session_key = None
        seen_nonces: set = set()
        try:
            # --- Handshake ---
            hello = recv_json(conn)
            if hello.get('type') != MSG_CLIENT_HELLO:
                send_json(conn, {'type': MSG_ERROR, 'msg': 'Expected CLIENT_HELLO'})
                return
            username_attempt = hello['username']
            client_pub_pem = hello['public_key'].encode()

            send_json(conn, {'type': MSG_SERVER_HELLO, 'public_key': self._server_pub.decode()})

            req = recv_json(conn)
            req_type = req.get('type')

            if req_type == MSG_REGISTER_REQUEST:
                print(f"[debug] Processing REGISTER_REQUEST for {username_attempt}", flush=True)
                try:
                    print("[debug] Decrypting password...", flush=True)
                    password = rsa_decrypt(self._server_priv, bytes.fromhex(req['password'])).decode()
                    print("[debug] Calling register()...", flush=True)
                    register(self._db_path, username_attempt, password)
                    print("[debug] Sending REGISTER_OK...", flush=True)
                    send_json(conn, {'type': MSG_REGISTER_OK})
                except ValueError as e:
                    print(f"[debug] ValueError: {e}", flush=True)
                    send_json(conn, {'type': MSG_REGISTER_FAIL, 'msg': str(e)})
                return

            if req_type != MSG_LOGIN_REQUEST:
                send_json(conn, {'type': MSG_ERROR, 'msg': 'Expected LOGIN_REQUEST or REGISTER_REQUEST'})
                return

            try:
                password = rsa_decrypt(self._server_priv, bytes.fromhex(req['password'])).decode()
                ok = login(self._db_path, username_attempt, password)
            except ValueError as e:
                send_json(conn, {'type': MSG_AUTH_FAIL, 'msg': str(e)})
                return

            if not ok:
                send_json(conn, {'type': MSG_AUTH_FAIL, 'msg': 'Invalid credentials'})
                return

            session_key = generate_session_key()
            wrapped = wrap_session_key(session_key, client_pub_pem)
            token = issue_token(username_attempt, self._server_priv)
            send_json(conn, {
                'type': MSG_AUTH_OK,
                'token': token.decode(),
                'session_key_wrapped': wrapped.hex(),
            })

            username = username_attempt
            with self._lock:
                self._clients[username] = (conn, session_key)
            print(f"[server] {username} connected from {addr}")

            # --- Chat loop ---
            while True:
                data = recv_frame(conn, session_key, seen_nonces)
                msg = data.decode(errors='replace')
                print(f"[{username}] {msg}")
                self._broadcast(f"{username}: {msg}", exclude=username)

        except (ConnectionError, OSError):
            pass
        except ValueError as e:
            try:
                send_json(conn, {'type': MSG_ERROR, 'msg': str(e)})
            except Exception:
                pass
        finally:
            if username:
                with self._lock:
                    self._clients.pop(username, None)
                print(f"[server] {username} disconnected")
            conn.close()

    def _broadcast(self, message: str, exclude: str = '') -> None:
        with self._lock:
            recipients = [(u, s, k) for u, (s, k) in self._clients.items() if u != exclude]
        for _, sock, key in recipients:
            try:
                send_frame(sock, key, message.encode())
            except Exception:
                pass
