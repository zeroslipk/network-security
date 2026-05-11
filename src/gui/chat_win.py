"""Chat window — bubble layout."""
from __future__ import annotations

import queue
import time
import tkinter as tk

from src.gui import styles
from src.net.client import ChatClient


class ChatWindow:
    def __init__(self, root: tk.Tk, client: ChatClient, username: str):
        self._root = root
        self._client = client
        self._username = username
        self._closing = False
        self._inbox: queue.Queue = queue.Queue()
        self._placeholder = "Type a message..."

        root.title(f"Secure Chat — {username}")
        root.configure(bg=styles.BG)
        root.geometry("580x500")
        root.minsize(460, 360)

        # ── 1. Header (TOP) ───────────────────────────────────────────────────
        header = tk.Frame(root, bg=styles.SURFACE, height=54)
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)

        left = tk.Frame(header, bg=styles.SURFACE)
        left.pack(side=tk.LEFT, padx=14, pady=6)
        tk.Label(left, text="Group Chat", bg=styles.SURFACE,
                 fg=styles.FG, font=styles.FONT_BOLD).pack(anchor="w")
        sr = tk.Frame(left, bg=styles.SURFACE)
        sr.pack(anchor="w")
        self._status_dot = tk.Label(sr, text="●", fg=styles.SUCCESS,
                                    bg=styles.SURFACE, font=(styles.FONT_FAMILY, 9))
        self._status_dot.pack(side=tk.LEFT)
        self._status_label = tk.Label(sr, text=f"Connected as {username}",
                                      bg=styles.SURFACE, fg=styles.FG_MUTED,
                                      font=styles.FONT_SMALL)
        self._status_label.pack(side=tk.LEFT, padx=(4, 0))
        tk.Label(header, text="🔒", bg=styles.SURFACE, fg=styles.SUCCESS,
                 font=styles.FONT_BOLD).pack(side=tk.RIGHT, padx=14)
        tk.Frame(root, bg=styles.MUTED, height=1).pack(fill=tk.X, side=tk.TOP)

        # ── 2. Input bar (BOTTOM — must be packed before log) ─────────────────
        bottom = tk.Frame(root, bg=styles.BG)
        bottom.pack(fill=tk.X, side=tk.BOTTOM, padx=12, pady=8)

        # Input row: [entry] [send button]
        input_row = tk.Frame(bottom, bg=styles.ENTRY_BG,
                             highlightthickness=1,
                             highlightbackground=styles.MUTED,
                             highlightcolor=styles.ACCENT)
        input_row.pack(fill=tk.X)

        # Send button — packed FIRST (RIGHT) so expand=True on entry doesn't steal its space
        self._send_btn = tk.Frame(input_row, bg=styles.ACCENT,
                                  width=46, cursor="hand2")
        self._send_btn.pack(side=tk.RIGHT, fill=tk.Y)
        self._send_btn.pack_propagate(False)
        self._send_icon = tk.Label(self._send_btn, text="▶",
                                   bg=styles.ACCENT, fg="#ffffff",
                                   font=(styles.FONT_FAMILY, 14, "bold"),
                                   cursor="hand2")
        self._send_icon.pack(fill=tk.BOTH, expand=True)
        self._send_btn.bind("<Button-1>", lambda e: self._on_send())
        self._send_icon.bind("<Button-1>", lambda e: self._on_send())

        self._entry = tk.Text(
            input_row, bg=styles.ENTRY_BG, fg=styles.MUTED,
            font=styles.FONT_INPUT, insertbackground=styles.FG,
            relief=tk.FLAT, height=1, wrap=tk.WORD, padx=12, pady=7,
        )
        self._entry.insert("1.0", self._placeholder)
        self._entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(bottom, text="Enter to send  ·  Shift+Enter for new line",
                 bg=styles.BG, fg=styles.MUTED,
                 font=styles.FONT_SMALL).pack(anchor=tk.W, pady=(4, 0))

        # Separator above input
        tk.Frame(root, bg=styles.MUTED, height=1).pack(fill=tk.X, side=tk.BOTTOM)

        # ── 3. Message area (fills remaining space) ───────────────────────────
        log_outer = tk.Frame(root, bg=styles.BG)
        log_outer.pack(fill=tk.BOTH, expand=True)

        self._canvas = tk.Canvas(log_outer, bg=styles.BG, highlightthickness=0)
        sb = tk.Scrollbar(log_outer, orient=tk.VERTICAL, command=self._canvas.yview,
                          troughcolor=styles.BG, bg=styles.MUTED, width=5, relief=tk.FLAT)
        self._canvas.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._msg_frame = tk.Frame(self._canvas, bg=styles.BG)
        self._cwin = self._canvas.create_window((0, 0), window=self._msg_frame, anchor="nw")
        self._msg_frame.bind("<Configure>", lambda e: self._canvas.configure(
            scrollregion=self._canvas.bbox("all")))
        self._canvas.bind("<Configure>", lambda e: self._canvas.itemconfig(
            self._cwin, width=e.width))
        self._canvas.bind_all("<MouseWheel>",
                              lambda e: self._canvas.yview_scroll(
                                  int(-1 * (e.delta / 120)), "units"))

        # Bindings
        self._entry.bind("<FocusIn>",      self._focus_in)
        self._entry.bind("<FocusOut>",     self._focus_out)
        self._entry.bind("<Return>",       self._on_return_key)
        self._entry.bind("<Shift-Return>", self._on_shift_return_key)
        self._entry.focus_set()

        root.protocol("WM_DELETE_WINDOW", self._on_close)
        client.start_receive_thread(self._inbox.put)
        self._add_date_sep(time.strftime("Today, %B %d"))
        self._add_system(f"Connected at {time.strftime('%H:%M:%S')}")
        self._poll_inbox()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _scroll_bottom(self):
        self._root.after(60, lambda: self._canvas.yview_moveto(1.0))

    def _focus_in(self, _):
        if self._entry.get("1.0", tk.END).strip() == self._placeholder:
            self._entry.delete("1.0", tk.END)
            self._entry.config(fg=styles.FG)

    def _focus_out(self, _):
        if not self._entry.get("1.0", tk.END).strip():
            self._entry.insert("1.0", self._placeholder)
            self._entry.config(fg=styles.MUTED)

    def _add_date_sep(self, label: str):
        row = tk.Frame(self._msg_frame, bg=styles.BG)
        row.pack(fill=tk.X, pady=(12, 4))
        tk.Frame(row, bg=styles.MUTED, height=1).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(16, 8), pady=6)
        tk.Label(row, text=label, bg=styles.BG, fg=styles.FG_MUTED,
                 font=styles.FONT_SMALL).pack(side=tk.LEFT)
        tk.Frame(row, bg=styles.MUTED, height=1).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 16), pady=6)

    def _add_system(self, text: str):
        tk.Label(self._msg_frame, text=text, bg=styles.BG,
                 fg=styles.MUTED, font=styles.FONT_SMALL).pack(pady=2)
        self._scroll_bottom()

    def _add_bubble(self, sender: str, text: str, is_self: bool, ts: str):
        wrap = max(260, int((self._canvas.winfo_width() or 580) * 0.58))
        row = tk.Frame(self._msg_frame, bg=styles.BG)
        row.pack(fill=tk.X, padx=12, pady=(2, 5))
        if is_self:
            tk.Label(row, text=f"You, {ts}", bg=styles.BG,
                     fg=styles.FG_MUTED, font=styles.FONT_SMALL).pack(anchor="e", pady=(0, 2))
            tk.Label(row, text=text, bg=styles.ACCENT, fg="#ffffff",
                     font=styles.FONT, wraplength=wrap,
                     justify=tk.LEFT, padx=12, pady=8).pack(anchor="e")
        else:
            tk.Label(row, text=f"{sender}, {ts}", bg=styles.BG,
                     fg=styles.FG_MUTED, font=styles.FONT_SMALL).pack(anchor="w", pady=(0, 2))
            tk.Label(row, text=text, bg=styles.ENTRY_BG, fg=styles.FG,
                     font=styles.FONT, wraplength=wrap,
                     justify=tk.LEFT, padx=12, pady=8).pack(anchor="w")
        self._scroll_bottom()

    # ── Event handlers ────────────────────────────────────────────────────────

    def _on_return_key(self, _) -> str:
        self._on_send()
        return "break"

    def _on_shift_return_key(self, _) -> str:
        self._entry.insert(tk.INSERT, "\n")
        return "break"

    def _on_send(self):
        text = self._entry.get("1.0", tk.END).strip()
        if not text or text == self._placeholder:
            return
        try:
            self._client.send(text)
        except Exception as e:
            self._set_disconnected(f"Send failed: {e}")
            return
        self._add_bubble("you", text, is_self=True, ts=time.strftime("%H:%M"))
        self._entry.delete("1.0", tk.END)
        self._entry.config(fg=styles.FG)

    def _poll_inbox(self):
        if self._closing:
            return
        try:
            while True:
                msg = self._inbox.get_nowait()
                ts = time.strftime("%H:%M")
                if ": " in msg:
                    sender, body = msg.split(": ", 1)
                    self._add_bubble(sender, body, is_self=False, ts=ts)
                else:
                    self._add_system(msg)
        except queue.Empty:
            pass
        self._root.after(50, self._poll_inbox)

    def _set_disconnected(self, reason: str):
        self._status_dot.config(fg=styles.ERROR)
        self._status_label.config(text=f"Disconnected — {reason}")
        self._send_btn.config(bg=styles.MUTED)
        self._send_icon.config(bg=styles.MUTED)
        self._entry.config(state=tk.DISABLED)

    def _on_close(self):
        self._closing = True
        try:
            self._client.close()
        except Exception:
            pass
        self._root.destroy()
