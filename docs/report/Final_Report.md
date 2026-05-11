# Secure Communication Suite — Final Report
**CSE451: Computer and Network Security**
**Ain Shams University**

## 1. Project Overview
The Secure Communication Suite is a comprehensive Python application that integrates core cryptographic algorithms to build a secure TCP chat application. It provides data confidentiality, integrity, authentication, and secure key management. The application successfully fulfills the requirements set out in the CSE451 project specification.

## 2. Implementation Details

### Phase 1 & 2: Cryptographic Modules
- **Symmetric Encryption:** AES-256 in GCM mode is used for all post-handshake chat messages. GCM provides both confidentiality and authentication. Keys are 256 bits, generated via CSPRNG (`os.urandom`).
- **Asymmetric Encryption:** RSA-2048 is used for key exchange and digital signatures. The suite uses RSA-OAEP for encrypting session keys and login passwords over the network, and RSA-PSS for signing session tokens.
- **Hashing:** SHA-256 and HMAC-SHA256 were implemented entirely from scratch per FIPS 180-4 and RFC 2104. They successfully pass NIST Known Answer Test (KAT) vectors.
- **Key Derivation (KDF):** PBKDF2-HMAC-SHA256 was implemented from scratch per RFC 8018, using 200,000 iterations to resist brute-force and dictionary attacks.

### Phase 3: Key Management and Authentication
- **Key Management:** An encrypted-at-rest keystore stores the user's RSA keys. The keystore is protected by a master key derived from the user's password using our custom PBKDF2 implementation and encrypted using AES-256-GCM.
- **Authentication:** Users register and log in via a custom protocol. Passwords are never transmitted in plaintext; they are encrypted client-side using the server's public key (RSA-OAEP) before transmission. Authentication checks are protected against timing attacks using constant-time comparisons (`hmac.compare_digest`). The system locks an account after 5 failed attempts to prevent online guessing attacks.

### Phase 4: Internet Services Integration
- **Chat Protocol:** A multi-threaded TCP server handles concurrent clients. The protocol features a handshake where the client validates the server's identity (Trust-On-First-Use Server Key Pinning), and the server provisions a fresh AES-256 session key wrapped in the client's public key.
- **Wire Framing:** Each message is framed with a 4-byte length prefix, a 12-byte unique nonce, the AES-GCM ciphertext, the GCM tag, and a final HMAC-SHA256 to ensure robust integrity and prevent replay attacks.

## 3. Security Analysis (STRIDE)
- **Spoofing:** Mitigated. Clients are authenticated via PBKDF2 passwords and issued RSA-PSS signed session tokens. The server's identity is pinned by the client (TOFU).
- **Tampering:** Mitigated. Every message frame includes a 16-byte AES-GCM tag and a 32-byte HMAC-SHA256. Any modified bits will result in the receiver dropping the frame.
- **Repudiation:** Mitigated partially. Session tokens are digitally signed, proving the server authenticated the user. However, chat messages use symmetric HMAC, meaning either party could have authored a message within the session.
- **Information Disclosure:** Mitigated. No plaintext passwords cross the network (encrypted via RSA-OAEP). The local keystore is AES-GCM encrypted.
- **Denial of Service:** Partially Mitigated. Account lockout prevents brute-force login DoS, but the TCP server remains vulnerable to high-volume connection flooding.
- **Elevation of Privilege:** Mitigated. Clients run in isolated threads with strict protocol state machines.

## 4. Testing Results
The suite includes an extensive testing pipeline covering unit, integration, and security scenarios.

### Automated Test Output
```text
============================= test session starts ==============================
collected 59 items

tests/test_block_cipher.py .......                                       [ 11%]
tests/test_public_key.py .......                                         [ 23%]
tests/test_hashing.py .......                                            [ 35%]
tests/test_kdf.py ....                                                   [ 42%]
tests/test_keymgmt.py ..........                                         [ 59%]
tests/test_auth.py ..........                                            [ 76%]
tests/test_integration.py ..............                                 [100%]

============================== 59 passed in 4.12s ==============================
```
- **NIST KAT Vectors:** Our from-scratch SHA-256 implementation perfectly matches the NIST expected hash outputs.
- **Smoke Tests:** `smoke_test.py` and `gui_smoke_test.py` pass cleanly, simulating concurrent user interactions.

### Security Demonstrations
Three scripts in the `demos/` folder provide practical demonstrations of the system's defenses:
1. **Eavesdropping (`demos/eavesdrop.py`):** Demonstrates that intercepting network frames yields only unintelligible ciphertext without the session key.
2. **Tampering (`demos/tamper.py`):** Demonstrates that flipping a single bit in transit causes the HMAC verification to fail, dropping the malicious frame.
3. **Replay Attack (`demos/replay.py`):** Demonstrates that capturing and resending a valid frame is blocked because the server caches and rejects duplicate nonces.

## 5. Known Limitations & Future Work
- **Perfect Forward Secrecy (PFS):** Currently, the session key is encrypted with the client's long-term RSA key. Future work should implement Diffie-Hellman Key Exchange (ECDHE) to achieve PFS.
- **Certificate Authority (PKI):** The server's identity currently relies on Trust-On-First-Use (TOFU). A robust PKI integration would improve identity verification.
- **Message Queues:** While the `EncryptionWorker` is available, the chat loop currently uses synchronous encryption. High-throughput environments would benefit from fully utilizing the asynchronous queues.

## 6. Team Contributions
*(Students: Please fill in your specific team contributions here before converting to Word/PDF)*

- Student 1: 
- Student 2: 
- Student 3: 
- Student 4: 
- Student 5: 
