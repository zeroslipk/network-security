"""
RSA-2048 asymmetric cryptography using pycryptodome.
Provides: keygen, PEM export/import, OAEP encrypt/decrypt, PSS sign/verify.
"""

from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Signature import pss
from Crypto.Hash import SHA256


def generate_keypair() -> tuple[bytes, bytes]:
    """Return (private_key_pem, public_key_pem) as bytes."""
    key = RSA.generate(2048)
    return key.export_key(), key.publickey().export_key()


def load_private_key(pem: bytes) -> RSA.RsaKey:
    return RSA.import_key(pem)


def load_public_key(pem: bytes) -> RSA.RsaKey:
    return RSA.import_key(pem)


def encrypt(public_key_pem: bytes, plaintext: bytes) -> bytes:
    """RSA-OAEP encrypt. For key transport only (max ~190 bytes for 2048-bit key)."""
    key = RSA.import_key(public_key_pem)
    cipher = PKCS1_OAEP.new(key, hashAlgo=SHA256)
    return cipher.encrypt(plaintext)


def decrypt(private_key_pem: bytes, ciphertext: bytes) -> bytes:
    """RSA-OAEP decrypt."""
    key = RSA.import_key(private_key_pem)
    cipher = PKCS1_OAEP.new(key, hashAlgo=SHA256)
    return cipher.decrypt(ciphertext)


def sign(private_key_pem: bytes, message: bytes) -> bytes:
    """RSA-PSS sign. Returns signature bytes."""
    key = RSA.import_key(private_key_pem)
    h = SHA256.new(message)
    return pss.new(key).sign(h)


def verify(public_key_pem: bytes, message: bytes, signature: bytes) -> bool:
    """RSA-PSS verify. Returns True on valid signature, False otherwise."""
    key = RSA.import_key(public_key_pem)
    h = SHA256.new(message)
    try:
        pss.new(key).verify(h, signature)
        return True
    except (ValueError, TypeError):
        return False
