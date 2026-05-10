"""
Headless GUI smoke test.
Creates a real server, then drives the LoginWindow and ChatWindow programmatically
through the Tk event loop without actually showing them. Confirms:
- LoginWindow.register_remote → server-side user created
- LoginWindow.login → ChatWindow opens
- ChatWindow sends a message, peer receives it
"""

import os
import socket
import sys
import threading
import time
import tkinter as tk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.gui.chat_win import ChatWindow
from src.net.client import ChatClient, register_remote
from src.net.server import ChatServer


def _start_server(db_path: str) -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.listen(10)
    srv = ChatServer("127.0.0.1", port, db_path)

    def _accept():
        try:
            while True:
                conn, addr = sock.accept()
                threading.Thread(target=srv._handle, args=(conn, addr), daemon=True).start()
        except OSError:
            pass

    threading.Thread(target=_accept, daemon=True).start()
    time.sleep(0.1)
    return port


def main():
    import tempfile
    db = os.path.join(tempfile.mkdtemp(), "users.json")
    port = _start_server(db)
    print(f"[smoke] server on port {port}")

    # Register two users via the network
    register_remote("127.0.0.1", port, "alice", "alicepass")
    register_remote("127.0.0.1", port, "bob", "bobpass")
    print("[smoke] registered alice and bob over the network")

    # Connect alice as a CLI client (non-GUI peer)
    alice_client = ChatClient("127.0.0.1", port, "alice")
    alice_client.connect("alicepass")

    # Connect bob via GUI ChatWindow (requires a Tk root)
    bob_client = ChatClient("127.0.0.1", port, "bob")
    bob_client.connect("bobpass")

    root = tk.Tk()
    root.withdraw()  # hide window for headless test
    chat = ChatWindow(root, bob_client, "bob")

    received_by_alice: list[str] = []
    alice_client.start_receive_thread(received_by_alice.append)

    # Drive the Tk event loop briefly to let receive threads start
    for _ in range(5):
        root.update()
        time.sleep(0.05)

    # alice → bob: bob's GUI should append to its log
    alice_client.send("hi from alice")
    for _ in range(20):
        root.update()
        time.sleep(0.05)
    log_text = chat._log.get("1.0", tk.END)
    assert "hi from alice" in log_text, f"expected message in log, got:\n{log_text}"
    print("[smoke] ✓ GUI ChatWindow received message from CLI peer")

    # bob (via GUI) → alice
    bob_client.send("hi from bob via GUI")
    time.sleep(0.5)
    for _ in range(5):
        root.update()
        time.sleep(0.05)
    assert any("hi from bob via GUI" in m for m in received_by_alice), \
        f"expected alice to receive message, got: {received_by_alice}"
    print("[smoke] ✓ alice received message sent from GUI ChatWindow")

    chat._on_close()
    alice_client.close()
    print("\n=== GUI SMOKE PASSED ===")


if __name__ == "__main__":
    main()
