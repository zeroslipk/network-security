"""
Scenario 1: Eavesdropping
Demonstrates that an attacker on the network only sees ciphertext and cannot
recover the plaintext without the session key.
"""
from src.crypto.block_cipher import encrypt, decrypt
from src.crypto.hashing import hmac_sha256
from src.keymgmt.key_exchange import generate_session_key

def demo_eavesdrop():
    print("--- EAVESDROP DEMO ---")
    session_key = generate_session_key()
    plaintext = b"Secret attack plan at dawn!"
    print(f"Alice sends: {plaintext}")
    
    nonce, ct, tag = encrypt(session_key, plaintext)
    mac = hmac_sha256(session_key, nonce + ct + tag)
    
    print("\n[Attacker intercepts frame on wire]")
    print(f"Nonce (12B): {nonce.hex()}")
    print(f"Ciphertext (NB): {ct.hex()}")
    print(f"GCM Tag (16B): {tag.hex()}")
    print(f"HMAC (32B): {mac.hex()}")
    print("\nAttacker tries to decrypt without session key...")
    try:
        wrong_key = b'\x00' * 32
        decrypt(wrong_key, nonce, ct, tag)
    except Exception as e:
        print(f"Result: Failed! ({type(e).__name__}: {e})")
        print("Confidentiality is maintained.")

if __name__ == "__main__":
    demo_eavesdrop()
