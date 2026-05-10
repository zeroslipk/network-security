# Software Requirements Specification
## Secure Communication Suite

**Course:** CSE451 Computer & Network Security  
**Institution:** Ain Shams University, Faculty of Engineering — Computer & Systems Eng. Dept.  
**Semester:** CHEP Spring 2026  
**Due Date:** Friday, May 8, 2026

---

## 1. Introduction

### 1.1 Purpose
This document specifies the functional and non-functional requirements for the Secure Communication Suite — a Python application that demonstrates the practical integration of core cryptographic techniques to protect data in transit and at rest.

### 1.2 Scope
The suite provides:
- Symmetric encryption via AES-256-GCM
- Asymmetric encryption and digital signatures via RSA-2048
- Data integrity verification via SHA-256 and HMAC-SHA256 (both implemented from scratch)
- Password-based key derivation via PBKDF2-HMAC-SHA256 (from scratch)
- Encrypted at-rest key storage
- Password-based user authentication
- A secure TCP chat application that exercises all of the above

### 1.3 Definitions

| Term | Definition |
|---|---|
| AES | Advanced Encryption Standard (FIPS 197) |
| GCM | Galois/Counter Mode — authenticated encryption mode for AES |
| RSA | Rivest–Shamir–Adleman public-key cryptosystem |
| OAEP | Optimal Asymmetric Encryption Padding (for RSA encryption) |
| PSS | Probabilistic Signature Scheme (for RSA signing) |
| SHA-256 | Secure Hash Algorithm 256-bit (FIPS 180-4) |
| HMAC | Hash-based Message Authentication Code (RFC 2104) |
| PBKDF2 | Password-Based Key Derivation Function 2 (RFC 8018) |
| Session key | A fresh symmetric AES key generated per chat session |
| Keystore | An encrypted file storing persistent cryptographic keys |

---

## 2. Key Components of the Secure Communication Suite

The suite is composed of six modules that answer the Phase 1 question "What are the key components?":

1. **Block Cipher Module** (`src/crypto/block_cipher.py`)
2. **Public Key Cryptosystem Module** (`src/crypto/public_key.py`)
3. **Hashing Module** (`src/crypto/hashing.py` + `src/crypto/kdf.py`)
4. **Key Management Module** (`src/keymgmt/`)
5. **Authentication Module** (`src/auth/`)
6. **Internet Services Security Module** (`src/net/` + `src/cli/`)

---

## 3. Cryptographic Techniques

Answers the Phase 1 question "What cryptographic techniques will be used?":

| Technique | Algorithm | Standard | Notes |
|---|---|---|---|
| Symmetric encryption | AES-256-GCM | FIPS 197, NIST SP 800-38D | Provides both confidentiality and authenticity (AEAD) |
| Asymmetric encryption | RSA-2048-OAEP | PKCS#1 / RFC 8017 | Used for session-key transport |
| Digital signatures | RSA-2048-PSS | PKCS#1 / RFC 8017 | Used for auth tokens and ClientHello signing |
| Hashing | SHA-256 | FIPS 180-4 | Implemented from scratch |
| MAC | HMAC-SHA256 | RFC 2104 | Implemented from scratch on top of our SHA-256 |
| Key derivation | PBKDF2-HMAC-SHA256 | RFC 8018 | 200 000 iterations, 32-byte output, implemented from scratch |
| Random generation | OS CSPRNG | via `os.urandom` | Used for nonces, salts, key material |

---

## 4. Functional Requirements

### 4.1 Block Cipher Module

| ID | Requirement |
|---|---|
| BC-1 | Encrypt a byte string using AES-256-GCM and return `(nonce, ciphertext, tag)`. |
| BC-2 | Decrypt `(nonce, ciphertext, tag)` using the same key and verify the GCM tag. |
| BC-3 | Raise an exception if tag verification fails (do not return partial plaintext). |
| BC-4 | Provide a `EncryptionWorker` thread that reads from a `plaintext_queue` and writes `(nonce, ciphertext, tag)` to a `ciphertext_queue`. |

### 4.2 Public Key Cryptosystem Module

| ID | Requirement |
|---|---|
| PK-1 | Generate an RSA-2048 key pair. |
| PK-2 | Export/import public and private keys in PEM format. |
| PK-3 | Encrypt a byte string with a public key using OAEP padding. |
| PK-4 | Decrypt with the corresponding private key. |
| PK-5 | Sign a byte string with a private key using PSS padding. |
| PK-6 | Verify a signature with a public key; return `True`/`False`. |

### 4.3 Hashing Module

| ID | Requirement |
|---|---|
| H-1 | Compute SHA-256 of any byte string, implemented from scratch per FIPS 180-4 (no use of `hashlib`). |
| H-2 | Pass all NIST SHA-256 Known Answer Test (KAT) vectors. |
| H-3 | Compute HMAC-SHA256 from scratch using our SHA-256. |
| H-4 | Compute PBKDF2-HMAC-SHA256 from scratch using our HMAC. |

### 4.4 Key Management Module

| ID | Requirement |
|---|---|
| KM-1 | Store a named key in an AES-GCM encrypted file (keystore). |
| KM-2 | Load a named key from the keystore; fail with an exception on wrong password. |
| KM-3 | List all key names stored in the keystore. |
| KM-4 | Delete a key from the keystore. |
| KM-5 | The keystore master key is derived from the user's password via PBKDF2. |
| KM-6 | Perform RSA-OAEP wrapping of an AES session key for transmission to a peer. |
| KM-7 | Unwrap a received RSA-OAEP-wrapped session key using the private key. |

### 4.5 Authentication Module

| ID | Requirement |
|---|---|
| AU-1 | Register a user by storing `(username, salt, PBKDF2(password, salt, 200_000))`. |
| AU-2 | Authenticate a login attempt using constant-time comparison. |
| AU-3 | Reject login after 5 consecutive failures (lockout). |
| AU-4 | Issue a signed session token `{username, expiry, nonce}` upon successful login. |
| AU-5 | Verify a session token's RSA-PSS signature and expiry before granting access. |

### 4.6 Internet Services Security Module (Secure Chat)

| ID | Requirement |
|---|---|
| IS-1 | Server listens for TCP connections and handles multiple clients concurrently via threads. |
| IS-2 | Each client completes a handshake: `ClientHello → ServerHello → LoginRequest → AuthOK + SessionKey`. |
| IS-3 | All post-handshake messages are encrypted with AES-256-GCM and authenticated with HMAC-SHA256. |
| IS-4 | Nonces are unique per message; replayed messages are rejected. |
| IS-5 | A CLI entry point allows `register`, `login`, and `chat` commands. |

---

## 5. Non-Functional Requirements

| ID | Requirement |
|---|---|
| NF-1 | All cryptographic primitives use keys of adequate size: AES-256, RSA-2048. |
| NF-2 | Passwords are never stored or transmitted in plaintext. |
| NF-3 | PBKDF2 uses at least 200 000 iterations. |
| NF-4 | AES nonces are generated via `os.urandom(12)` and never reused within a session. |
| NF-5 | Timing-safe comparison is used wherever passwords or MACs are compared. |
| NF-6 | The keystore file is never written with plaintext key material. |
| NF-7 | The suite runs on Python 3.11+ on Linux, macOS, and Windows. |
| NF-8 | All modules include unit tests with known-answer vectors. |

---

## 6. User Stories (from spec)

1. As a user, I want to encrypt my messages using a block cipher so that they can be securely transmitted. → **BC-1, BC-4, IS-3**
2. As a user, I want to use public key cryptosystems to securely share keys with my communication partner. → **PK-3, PK-4, KM-6, KM-7, IS-2**
3. As a user, I want to verify the integrity of my received messages using hashing functions. → **H-3, IS-3**
4. As a user, I want to manage my cryptographic keys securely. → **KM-1 through KM-7**
5. As a user, I want to authenticate myself to the system to ensure secure access. → **AU-1 through AU-5**
6. As a user, I want to secure my internet services using the provided cryptographic modules. → **IS-1 through IS-5**

---

## 7. Out of Scope

- GUI (deferred as stretch goal)
- X.509 certificate issuance (stretch goal)
- Perfect Forward Secrecy via ECDH (stretch goal)
- Protection against denial-of-service attacks
- IPv6 support
