"""
Tests for src/crypto/block_cipher.py (AES-256-GCM + EncryptionWorker).
"""

import queue
from src.crypto.block_cipher import encrypt, decrypt, generate_key, EncryptionWorker


def test_roundtrip():
    key = generate_key()
    plaintext = b"Hello, World!"
    nonce, ciphertext, tag = encrypt(key, plaintext)
    assert decrypt(key, nonce, ciphertext, tag) == plaintext


def test_ciphertext_differs_from_plaintext():
    key = generate_key()
    plaintext = b"Secret message"
    _, ciphertext, _ = encrypt(key, plaintext)
    assert ciphertext != plaintext


def test_unique_nonces():
    key = generate_key()
    nonces = {encrypt(key, b"msg")[0] for _ in range(100)}
    assert len(nonces) == 100  # all nonces should be unique


def test_tampered_ciphertext_rejected():
    key = generate_key()
    nonce, ciphertext, tag = encrypt(key, b"important data")
    tampered = bytes([ciphertext[0] ^ 0xFF]) + ciphertext[1:]
    try:
        decrypt(key, nonce, tampered, tag)
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_tampered_tag_rejected():
    key = generate_key()
    nonce, ciphertext, tag = encrypt(key, b"data")
    bad_tag = bytes([tag[0] ^ 0x01]) + tag[1:]
    try:
        decrypt(key, nonce, ciphertext, bad_tag)
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_wrong_key_rejected():
    key1 = generate_key()
    key2 = generate_key()
    nonce, ciphertext, tag = encrypt(key1, b"data")
    try:
        decrypt(key2, nonce, ciphertext, tag)
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_encryption_worker():
    key = generate_key()
    pt_q: queue.Queue = queue.Queue()
    ct_q: queue.Queue = queue.Queue()
    worker = EncryptionWorker(key, pt_q, ct_q)
    worker.start()

    messages = [b"msg1", b"msg2", b"msg3"]
    for m in messages:
        pt_q.put(m)
    pt_q.put(None)  # stop signal
    worker.join(timeout=5)

    results = []
    while not ct_q.empty():
        results.append(ct_q.get())

    assert len(results) == len(messages)
    for original, (nonce, ct, tag) in zip(messages, results):
        assert decrypt(key, nonce, ct, tag) == original


def test_key_is_32_bytes():
    assert len(generate_key()) == 32
