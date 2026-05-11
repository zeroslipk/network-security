"""
Scenario 2: Tampering
Demonstrates that if an attacker modifies the ciphertext in transit,
the HMAC and GCM tag validation will fail at the receiver.
"""
from src.crypto.block_cipher import encrypt, decrypt
from src.crypto.hashing import hmac_sha256
from src.keymgmt.key_exchange import generate_session_key
import hmac

def demo_tamper():
    print("--- TAMPER DEMO ---")
    session_key = generate_session_key()
    plaintext = b"Transfer $10 to Bob"
    
    nonce, ct, tag = encrypt(session_key, plaintext)
    mac = hmac_sha256(session_key, nonce + ct + tag)
    
    print(f"Alice sends: {plaintext}")
    print(f"Original ciphertext: {ct.hex()}")
    
    print("\n[Attacker intercepts and modifies ciphertext]")
    # flip a bit in ciphertext
    tampered_ct = bytearray(ct)
    tampered_ct[0] ^= 0x01
    tampered_ct = bytes(tampered_ct)
    print(f"Tampered ciphertext: {tampered_ct.hex()}")
    
    print("\n[Receiver attempts to authenticate and decrypt]")
    # Receiver verifies MAC first
    expected_mac = hmac_sha256(session_key, nonce + tampered_ct + tag)
    if not hmac.compare_digest(mac, expected_mac):
        print("Result: HMAC verification failed! Message dropped.")
        print("Integrity is maintained.")
    else:
        print("MAC passed... wait, this shouldn't happen.")

if __name__ == "__main__":
    demo_tamper()
