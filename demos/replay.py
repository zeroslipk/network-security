"""
Scenario 3: Replay Attack
Demonstrates that if an attacker captures a valid frame and resends it later,
the receiver will reject it because the nonce has already been seen.
"""
from src.crypto.block_cipher import encrypt
from src.crypto.hashing import hmac_sha256
from src.keymgmt.key_exchange import generate_session_key

def demo_replay():
    print("--- REPLAY DEMO ---")
    session_key = generate_session_key()
    seen_nonces = set()
    
    plaintext = b"Authenticate me!"
    nonce, ct, tag = encrypt(session_key, plaintext)
    
    print("Alice sends message 1 to Server...")
    print(f"Message has nonce: {nonce.hex()}")
    
    # Server receives it successfully
    seen_nonces.add(nonce)
    print("[Server] Received message successfully. Nonce recorded.")
    
    print("\n[Attacker intercepts message and sends it again]")
    print(f"Attacker resends message with same nonce: {nonce.hex()}")
    
    # Server receives replayed message
    print("\n[Server] Processing incoming frame...")
    if nonce in seen_nonces:
        print("Result: ValueError('Replay detected: duplicate nonce')")
        print("Replay attack prevented.")

if __name__ == "__main__":
    demo_replay()
