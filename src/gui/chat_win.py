"""
Chat window. Displays messages from the connected ChatClient and lets the
user send new ones.
"""

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

        root.title(f"Secure Chat — {username}")
        root.configure(bg=styles.BG)
        root.geometry("640x480")

        # Status bar
        self._status_bar = tk.Frame(root, bg=styles.BG, height=28)
        self._status_bar.pack(fill=tk.X, side=tk.TOP)
        self._status_dot = tk.Label(
            self._status_bar, text="●", fg=styles.SUCCESS, bg=styles.BG,
            font=styles.FONT_BOLD,
        )
        self._status_dot.pack(side=tk.LEFT, padx=(10, 4))
        self._status_label = tk.Label(
            self._status_bar, text=f"Connected as {username}",
            bg=styles.BG, fg=styles.FG, font=styles.FONT,
        )
        self._status_label.pack(side=tk.LEFT)

        # Message log
        log_frame = tk.Frame(root, bg=styles.BG)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(4, 4))
        self._log = tk.Text(
            log_frame, bg=styles.ENTRY_BG, fg=styles.FG,
            font=styles.FONT, relief=tk.FLAT, wrap=tk.WORD,
            state=tk.DISABLED,
        )
        scrollbar = tk.Scrollbar(log_frame, command=self._log.yview)
        self._log.config(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._log.tag_config("self", foreground=styles.ACCENT)
        self._log.tag_config("peer", foreground=styles.FG)
        self._log.tag_config("system", foreground=styles.MUTED)

        # Input bar
        input_frame = tk.Frame(root, bg=styles.BG)
        input_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=10)
        self._entry = tk.Entry(
            input_frame, bg=styles.ENTRY_BG, fg=styles.FG,
            font=styles.FONT, insertbackground=styles.FG, relief=tk.FLAT,
        )
        self._entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6)
        self._send_btn = tk.Button(
            input_frame, text="Send", command=self._on_send,
            bg=styles.ACCENT, fg=styles.BG, font=styles.FONT_BOLD,
            relief=tk.FLAT, padx=14,
        )
        self._send_btn.pack(side=tk.LEFT, padx=(8, 0))
        self._entry.focus_set()
        self._entry.bind("<Return>", lambda e: self._on_send())

        root.protocol("WM_DELETE_WINDOW", self._on_close)
        client.start_receive_thread(self._inbox.put)
        self._append(f"Connected to chat at {time.strftime('%H:%M:%S')}", tag="system")
        self._poll_inbox()

    def _append(self, text: str, tag: str = "peer") -> None:
        self._log.config(state=tk.NORMAL)
        self._log.insert(tk.END, text + "\n", tag)
        self._log.config(state=tk.DISABLED)
        self._log.see(tk.END)

    def _on_send(self) -> None:
        text = self._entry.get().strip()
        if not text:
            return
        try:
            self._client.send(text)
        except Exception as e:
            self._set_disconnected(f"Send failed: {e}")
            return
        ts = time.strftime("%H:%M:%S")
        self._append(f"[{ts}] you: {text}", tag="self")
        self._entry.delete(0, tk.END)

    def _poll_inbox(self) -> None:
        if self._closing:
            return
        try:
            while True:
                message = self._inbox.get_nowait()
                ts = time.strftime("%H:%M:%S")
                self._append(f"[{ts}] {message}", tag="peer")
        except queue.Empty:
            pass
        self._root.after(50, self._poll_inbox)

    def _set_disconnected(self, reason: str) -> None:
        self._status_dot.config(fg=styles.ERROR)
        self._status_label.config(text=f"Disconnected — {reason}")
        self._send_btn.config(state=tk.DISABLED)
        self._entry.config(state=tk.DISABLED)

    def _on_close(self) -> None:
        self._closing = True
        try:
            self._client.close()
        except Exception:
            pass
        self._root.destroy()
