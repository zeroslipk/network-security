"""
GUI entry point: python -m src.gui.app [--server HOST:PORT]
Opens the login window first; on successful auth, transitions to chat window.
"""

import argparse
import tkinter as tk

from src.gui.chat_win import ChatWindow
from src.gui.login_win import LoginWindow
from src.net.client import ChatClient


def main():
    parser = argparse.ArgumentParser(description="Secure Communication Suite GUI")
    parser.add_argument("--server", default="localhost:9000")
    args = parser.parse_args()

    root = tk.Tk()
    state = {"login": None, "client": None, "username": None}

    def _on_authenticated(client: ChatClient) -> None:
        state["client"] = client
        # Read the username BEFORE destroying the login widgets
        username = state["login"]._fields["username"].get().strip()
        for w in root.winfo_children():
            w.destroy()
        root.unbind("<Return>")
        ChatWindow(root, client, username)

    state["login"] = LoginWindow(root, args.server, _on_authenticated)
    root.mainloop()


if __name__ == "__main__":
    main()
