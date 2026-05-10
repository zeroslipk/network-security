"""
AES-256-GCM symmetric encryption wrapper.
Extends the EncryptionWorker skeleton from the project spec.
"""

import os
import queue
import threading
from Crypto.Cipher import AES


def encrypt(key: bytes, plaintext: bytes) -> tuple[bytes, bytes, bytes]:
    """Return (nonce, ciphertext, tag) using AES-256-GCM."""
    nonce = os.urandom(12)
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    ciphertext, tag = cipher.encrypt_and_digest(plaintext)
    return nonce, ciphertext, tag


def decrypt(key: bytes, nonce: bytes, ciphertext: bytes, tag: bytes) -> bytes:
    """Decrypt and verify tag. Raises ValueError on authentication failure."""
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    return cipher.decrypt_and_verify(ciphertext, tag)


def generate_key() -> bytes:
    """Generate a random 256-bit AES key."""
    return os.urandom(32)


class EncryptionWorker(threading.Thread):
    """
    Worker thread that encrypts plaintext from a queue.
    Extends the skeleton provided in the project spec.

    Reads bytes from plaintext_queue.
    Puts (nonce, ciphertext, tag) tuples into ciphertext_queue.
    Send None to plaintext_queue to stop the worker.
    """

    def __init__(self, key: bytes, plaintext_queue: queue.Queue, ciphertext_queue: queue.Queue):
        super().__init__(daemon=True)
        self._key = key
        self.plaintext_queue = plaintext_queue
        self.ciphertext_queue = ciphertext_queue

    def run(self):
        while True:
            plaintext = self.plaintext_queue.get()
            if plaintext is None:
                break
            self.ciphertext_queue.put(encrypt(self._key, plaintext))
