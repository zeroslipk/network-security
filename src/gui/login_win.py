"""
Login / Register window.
On success, calls on_authenticated(client) with a connected ChatClient.
"""

import threading
import tkinter as tk
from tkinter import ttk

from src.gui import styles
from src.net.client import ChatClient, register_remote


class LoginWindow:
    def __init__(self, root: tk.Tk, default_server: str, on_authenticated):
        self._root = root
        self._on_authenticated = on_authenticated

        root.title("Secure Communication Suite")
        root.configure(bg=styles.BG)
        root.geometry("420x340")
        root.resizable(False, False)

        title = tk.Label(
            root, text="Secure Communication Suite",
            bg=styles.BG, fg=styles.ACCENT, font=styles.FONT_TITLE,
        )
        title.pack(pady=(20, 10))

        form = tk.Frame(root, bg=styles.BG)
        form.pack(padx=30, pady=10, fill=tk.X)

        self._fields = {}
        for label_text, key, show in [
            ("Server", "server", None),
            ("Username", "username", None),
            ("Password", "password", "•"),
        ]:
            row = tk.Frame(form, bg=styles.BG)
            row.pack(fill=tk.X, pady=4)
            tk.Label(
                row, text=label_text + ":", width=10, anchor="w",
                bg=styles.BG, fg=styles.FG, font=styles.FONT,
            ).pack(side=tk.LEFT)
            entry = tk.Entry(
                row, bg=styles.ENTRY_BG, fg=styles.FG,
                font=styles.FONT, insertbackground=styles.FG, relief=tk.FLAT,
                show=show or "",
            )
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)
            self._fields[key] = entry

        self._fields["server"].insert(0, default_server)

        btn_row = tk.Frame(root, bg=styles.BG)
        btn_row.pack(pady=10)
        tk.Button(
            btn_row, text="Login", command=self._on_login,
            bg=styles.ACCENT, fg=styles.BG, font=styles.FONT_BOLD,
            relief=tk.FLAT, padx=20, pady=4,
        ).pack(side=tk.LEFT, padx=5)
        tk.Button(
            btn_row, text="Register", command=self._on_register,
            bg=styles.MUTED, fg=styles.FG, font=styles.FONT_BOLD,
            relief=tk.FLAT, padx=20, pady=4,
        ).pack(side=tk.LEFT, padx=5)

        self._status = tk.Label(
            root, text="", bg=styles.BG, fg=styles.MUTED,
            font=styles.FONT, wraplength=380,
        )
        self._status.pack(pady=10)

        self._fields["username"].focus_set()
        root.bind("<Return>", lambda e: self._on_login())

    def _read(self) -> tuple[str, int, str, str] | None:
        server = self._fields["server"].get().strip()
        username = self._fields["username"].get().strip()
        password = self._fields["password"].get()
        if not (server and username and password):
            self._set_status("All fields are required.", error=True)
            return None
        try:
            host, port_str = server.rsplit(":", 1)
            port = int(port_str)
        except ValueError:
            self._set_status("Server must be in HOST:PORT format.", error=True)
            return None
        return host, port, username, password

    def _set_status(self, text: str, error: bool = False, success: bool = False) -> None:
        color = styles.ERROR if error else styles.SUCCESS if success else styles.MUTED
        self._status.config(text=text, fg=color)

    def _disable_buttons(self, disabled: bool) -> None:
        state = tk.DISABLED if disabled else tk.NORMAL
        for child in self._root.winfo_children():
            if isinstance(child, tk.Frame):
                for grandchild in child.winfo_children():
                    if isinstance(grandchild, tk.Button):
                        grandchild.config(state=state)

    def _on_login(self) -> None:
        creds = self._read()
        if not creds:
            return
        host, port, username, password = creds
        self._set_status("Connecting...")
        self._disable_buttons(True)

        def _do_login():
            try:
                client = ChatClient(host, port, username)
                client.connect(password)
                self._root.after(0, lambda: self._on_authenticated(client))
            except PermissionError as e:
                err = str(e)
                self._root.after(0, lambda em=err: self._set_status(em, error=True))
                self._root.after(0, lambda: self._disable_buttons(False))
            except (ConnectionError, OSError) as e:
                err = f"Connection failed: {e}"
                self._root.after(0, lambda em=err: self._set_status(em, error=True))
                self._root.after(0, lambda: self._disable_buttons(False))

        threading.Thread(target=_do_login, daemon=True).start()

    def _on_register(self) -> None:
        creds = self._read()
        if not creds:
            return
        host, port, username, password = creds
        self._set_status("Registering...")
        self._disable_buttons(True)

        def _do_register():
            try:
                register_remote(host, port, username, password)
                msg = f"Registered '{username}'. Click Login to continue."
                self._root.after(0, lambda m=msg: self._set_status(m, success=True))
            except (ValueError, ConnectionError, OSError) as e:
                err = f"Registration failed: {e}"
                self._root.after(0, lambda em=err: self._set_status(em, error=True))
            finally:
                self._root.after(0, lambda: self._disable_buttons(False))

        threading.Thread(target=_do_register, daemon=True).start()
