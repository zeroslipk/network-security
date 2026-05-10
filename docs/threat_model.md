# Threat Model
## Secure Communication Suite

---

## 1. Assets Being Protected

| Asset | Where stored / transmitted |
|---|---|
| Message plaintext | In memory only; never written to disk in plaintext |
| AES session key | Transmitted RSA-OAEP wrapped; stored only in RAM during a session |
| User password | Never stored; only PBKDF2 output (salted hash) is persisted |
| RSA private key | In encrypted keystore on disk; unlocked in RAM per session |
| User database | `users.json` — contains only (username, salt, PBKDF2 hash) |

---

## 2. Threat Actors

| Actor | Capability |
|---|---|
| Passive eavesdropper | Captures raw TCP traffic (Wireshark / tcpdump) |
| Active MITM | Can intercept and modify TCP packets |
| Offline attacker | Has a copy of the keystore or user database |
| Malicious peer | A legitimate user attempting to impersonate another |
| Replay attacker | Records and retransmits previously captured frames |

---

## 3. STRIDE Analysis

### 3.1 Spoofing (identity theft)
- **Threat:** Attacker pretends to be a legitimate user or server.
- **Countermeasure:** 
  - Server authenticates clients via PBKDF2-hashed password comparison.
  - Client-to-server authentication via RSA-PSS signed LoginRequest.
  - Session tokens are RSA-PSS signed by the server; forgery requires the server private key.

### 3.2 Tampering (data modification)
- **Threat:** Attacker modifies ciphertext or MAC in transit.
- **Countermeasure:**
  - AES-256-GCM tag catches any ciphertext modification.
  - HMAC-SHA256 over `(nonce || ciphertext || tag)` provides a second integrity layer.
  - Any tamper → decryption fails → connection dropped; plaintext is never returned.

### 3.3 Repudiation (denial of action)
- **Threat:** A sender denies having sent a message.
- **Countermeasure:**
  - RSA-PSS signature on LoginRequest binds the session to the user's key pair.
  - Session token ties the AES session key to an authenticated identity.
  - *(Note: per-message non-repudiation is out of scope — HMAC is shared key, not signing.)*

### 3.4 Information Disclosure (eavesdropping)
- **Threat:** Passive attacker reads messages off the wire.
- **Countermeasure:**
  - All post-handshake messages encrypted with AES-256-GCM.
  - Session key never transmitted in plaintext (RSA-OAEP wrapped).
  - Passwords never sent; only PBKDF2 output compared server-side.

### 3.5 Denial of Service
- **Threat:** Attacker floods server with connections / malformed frames.
- **Countermeasure (partial):**
  - Login lockout after 5 failures per user prevents online brute-force.
  - *(Full DoS protection is out of scope for this project.)*

### 3.6 Elevation of Privilege
- **Threat:** Regular user gains access to another user's messages or keys.
- **Countermeasure:**
  - Per-user keystore protected by individual PBKDF2 master keys.
  - Session tokens include username and expiry; server verifies RSA-PSS signature before routing messages.
  - Nonce uniqueness check prevents session token replay.

---

## 4. Attack Scenarios and Defenses

### Scenario 1 — Eavesdropper reads TCP stream
**Attack:** Run `tcpdump -i lo` while two users chat.  
**Defense:** Wire contains only `nonce || AES-GCM-ciphertext || tag || HMAC`. No plaintext visible.  
**Verification:** `demos/eavesdrop.py` demonstrates this.

### Scenario 2 — Bit-flip attack on ciphertext
**Attack:** Flip one bit in the captured ciphertext before forwarding.  
**Defense:** AES-GCM tag verification fails → `ValueError` raised → server drops connection.  
**Verification:** `demos/tamper.py` demonstrates this.

### Scenario 3 — Replay attack
**Attack:** Record a valid encrypted frame and retransmit it.  
**Defense:** Each frame's nonce is checked against a per-session set of seen nonces. Duplicate → connection dropped.  
**Verification:** `demos/replay.py` demonstrates this.

### Scenario 4 — Offline dictionary attack on user database
**Attack:** Steal `users.json` and brute-force passwords.  
**Defense:** PBKDF2 with 200 000 iterations and a random 16-byte salt per user. At ~1 M iterations/sec on commodity hardware, a single guess costs 200 ms. A 10-character random password at 70-char alphabet = 2.8×10¹⁸ candidates ≈ centuries to crack.

### Scenario 5 — Offline attack on keystore
**Attack:** Steal `keystore.enc` and brute-force the master key.  
**Defense:** Master key = PBKDF2(password, salt, 200 000). Same cost as Scenario 4.

---

## 5. What the Suite Does NOT Protect Against

| Threat | Why out of scope |
|---|---|
| Malware on the endpoint | OS-level; cryptography cannot help if memory is compromised |
| Key compromise after the fact | No perfect forward secrecy (ECDH is a stretch goal) |
| Server-side compromise | Server holds session keys in RAM during a session |
| Distributed DoS | No rate limiting or IP blocking |
| Man-in-the-middle during initial key exchange | No PKI / certificate authority; first key exchange trusts the presented public key |

The MITM vulnerability during the first connection (before any trust anchor is established) is a known limitation. Adding X.509 certificates with a trusted CA is listed as a stretch goal in the project plan.
