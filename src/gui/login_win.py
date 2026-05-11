"""
Login / Register window.
On success, calls on_authenticated(client) with a connected ChatClient.
"""
from __future__ import annotations

import threading
import tkinter as tk

from src.gui import styles
from src.net.client import ChatClient, register_remote


class LoginWindow:
    def __init__(self, root: tk.Tk, default_server: str, on_authenticated):
        self._root = root
        self._on_authenticated = on_authenticated

        root.title("Secure Communication Suite")
        root.configure(bg=styles.BG)
        root.geometry("460x420")
        root.resizable(False, False)

        # ── Header ───────────────────────────────────────────────────────────
        header = tk.Frame(root, bg=styles.SURFACE)
        header.pack(fill=tk.X)
        tk.Label(
            header, text="🔒  Secure Communication Suite",
            bg=styles.SURFACE, fg=styles.FG,
            font=styles.FONT_TITLE, pady=18,
        ).pack()
        tk.Label(
            header, text="End-to-end encrypted · AES-256-GCM · RSA-2048",
            bg=styles.SURFACE, fg=styles.FG_MUTED,
            font=styles.FONT_SMALL, pady=(0),
        ).pack(pady=(0, 12))

        # ── Form ─────────────────────────────────────────────────────────────
        form = tk.Frame(root, bg=styles.BG)
        form.pack(padx=36, pady=20, fill=tk.X)

        self._fields: dict[str, tk.Entry] = {}
        for label_text, key, show in [
            ("Server",   "server",   None),
            ("Username", "username", None),
            ("Password", "password", "•"),
        ]:
            # Label
            tk.Label(
                form, text=label_text,
                bg=styles.BG, fg=styles.FG_MUTED,
                font=styles.FONT_SMALL, anchor="w",
            ).pack(fill=tk.X, pady=(8, 2))

            # Entry
            entry = tk.Entry(
                form, bg=styles.ENTRY_BG, fg=styles.FG,
                font=styles.FONT_INPUT,
                insertbackground=styles.FG,
                relief=tk.FLAT, show=show or "",
                highlightthickness=1,
                highlightcolor=styles.ACCENT,
                highlightbackground=styles.ENTRY_BG,
            )
            entry.pack(fill=tk.X, ipady=8)
            self._fields[key] = entry

        self._fields["server"].insert(0, default_server)

        # ── Buttons (Frame+Label to bypass macOS native button rendering) ───
        btn_row = tk.Frame(root, bg=styles.BG)
        btn_row.pack(pady=16, padx=36, fill=tk.X)

        self._login_frame = tk.Frame(btn_row, bg=styles.ACCENT2, cursor="hand2")
        self._login_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        self._login_lbl = tk.Label(
            self._login_frame, text="Login",
            bg=styles.ACCENT2, fg="#ffffff", font=styles.FONT_BOLD,
            pady=10, cursor="hand2",
        )
        self._login_lbl.pack(fill=tk.X)
        self._login_frame.bind("<Button-1>", lambda e: self._on_login())
        self._login_lbl.bind("<Button-1>", lambda e: self._on_login())

        self._register_frame = tk.Frame(btn_row, bg=styles.ENTRY_BG, cursor="hand2")
        self._register_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0))
        self._register_lbl = tk.Label(
            self._register_frame, text="Register",
            bg=styles.ENTRY_BG, fg=styles.FG, font=styles.FONT_BOLD,
            pady=10, cursor="hand2",
        )
        self._register_lbl.pack(fill=tk.X)
        self._register_frame.bind("<Button-1>", lambda e: self._on_register())
        self._register_lbl.bind("<Button-1>", lambda e: self._on_register())

        # ── Status ───────────────────────────────────────────────────────────
        self._status = tk.Label(
            root, text="", bg=styles.BG, fg=styles.MUTED,
            font=styles.FONT_SMALL, wraplength=400,
        )
        self._status.pack(pady=(0, 10))

        self._fields["username"].focus_set()
        root.bind("<Return>", lambda e: self._on_login())

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _read(self) -> tuple[str, int, str, str] | None:
        server   = self._fields["server"].get().strip()
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
        cursor = "arrow" if disabled else "hand2"
        fg_login = styles.MUTED if disabled else "#ffffff"
        fg_reg   = styles.MUTED if disabled else styles.FG
        for widget in (self._login_frame, self._login_lbl):
            widget.config(cursor=cursor)
        for widget in (self._register_frame, self._register_lbl):
            widget.config(cursor=cursor)
        self._login_lbl.config(fg=fg_login)
        self._register_lbl.config(fg=fg_reg)
        # Block clicks when disabled
        self._login_frame._disabled = disabled
        self._register_frame._disabled = disabled

    def _on_login(self) -> None:
        creds = self._read()
        if not creds:
            return
        host, port, username, password = creds
        self._set_status("Connecting... (generating RSA keys, ~5s)")
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
