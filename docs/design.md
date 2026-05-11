# Design Document
## Secure Communication Suite

---

## 1. Module Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    CLI Entry Point                           │
│                  src/cli/main.py                             │
└──────────────┬──────────────────────────────┬───────────────┘
               │                              │
    ┌──────────▼──────────┐       ┌──────────▼──────────┐
    │   src/net/server.py  │       │  src/net/client.py   │
    │   (TCP, threaded)    │       │  (TCP, REPL)         │
    └──────────┬──────────┘       └──────────┬──────────┘
               │                              │
               └──────────┬───────────────────┘
                          │
               ┌──────────▼──────────┐
               │  src/net/protocol.py │
               │  (framing, handshake │
               │   state machine)     │
               └──┬──────┬──────┬───┘
                  │      │      │
     ┌────────────▼┐ ┌───▼───┐ ┌▼────────────────┐
     │ src/auth/   │ │keymgmt│ │ src/crypto/      │
     │ password_   │ │key_   │ │ block_cipher.py  │
     │ auth.py     │ │exch.  │ │ public_key.py    │
     │ session.py  │ │keysto │ │ hashing.py       │
     └──────┬──────┘ │ re.py │ │ kdf.py           │
            │        └───┬───┘ └──────────────────┘
            │            │
            └────────────▼
                 (all depend on hashing.py + kdf.py)
```

---

## 2. File Responsibilities

| File | Responsibility |
|---|---|
| `src/crypto/hashing.py` | SHA-256 (FIPS 180-4 scratch impl), HMAC-SHA256 |
| `src/crypto/kdf.py` | PBKDF2-HMAC-SHA256 (RFC 8018 scratch impl) |
| `src/crypto/block_cipher.py` | AES-256-GCM encrypt/decrypt, `EncryptionWorker` thread |
| `src/crypto/public_key.py` | RSA-2048 keygen, OAEP encrypt/decrypt, PSS sign/verify |
| `src/keymgmt/keystore.py` | Encrypted-at-rest JSON keystore (AES-GCM, PBKDF2 master key) |
| `src/keymgmt/key_exchange.py` | RSA-OAEP wrapping/unwrapping of AES session keys |
| `src/auth/password_auth.py` | User registration, login, lockout |
| `src/auth/session.py` | Session token issuance (RSA-PSS) and verification |
| `src/net/protocol.py` | Wire frame format, `HandshakeState` machine |
| `src/net/server.py` | TCP server, per-client threads, routing |
| `src/net/client.py` | TCP client, handshake, chat REPL |
| `src/cli/main.py` | `register` / `server` / `chat` subcommands |

---

## 3. Wire Frame Format

Every message sent over TCP uses this binary frame:

```
 0       4       16                   N+16        N+32        N+64
 ┌───────┬────────┬────────────────────┬───────────┬──────────┐
 │ len   │ nonce  │   ciphertext       │  GCM tag  │  HMAC    │
 │ 4 B   │ 12 B   │   N bytes          │  16 B     │  32 B    │
 └───────┴────────┴────────────────────┴───────────┴──────────┘
```

- **len**: big-endian uint32 = total frame length (excluding the 4-byte len field itself)
- **nonce**: 12-byte random value from `os.urandom(12)`, unique per message
- **ciphertext**: AES-256-GCM ciphertext
- **GCM tag**: 16-byte authentication tag produced by AES-GCM
- **HMAC**: HMAC-SHA256 over `nonce || ciphertext || tag` using the session key, prevents tag stripping attacks

---

## 4. Handshake Sequence Diagram

```
Client                                          Server
  │                                               │
  │──── TCP connect ────────────────────────────►│
  │                                               │
  │──── ClientHello ────────────────────────────►│
  │     { username, RSA_pub_pem }                 │
  │                                               │
  │◄─── ServerHello ────────────────────────────│
  │     { server_RSA_pub_pem }                    │
  │                                               │
  │──── LoginRequest ───────────────────────────►│
  │     { username,                               │
  │       RSA-PSS( PBKDF2(password) ) }           │  auth.password_auth.login()
  │                                               │
  │◄─── AuthOK ─────────────────────────────────│
  │     { session_token,                          │  key_exchange.wrap_session_key()
  │       RSA-OAEP( aes_session_key ) }           │
  │                                               │
  │  [ESTABLISHED — all messages use AES-GCM]    │
  │                                               │
  │──── Frame(msg) ─────────────────────────────►│
  │◄─── Frame(msg) ─────────────────────────────│
  │                 ...                           │
```

Messages in the ESTABLISHED phase use the wire frame format defined in section 3.  
The AES session key is generated fresh by the server for each connection and wrapped with the client's RSA public key.

---

## 5. Key Management Architecture

```
User password
     │
     ▼  PBKDF2-HMAC-SHA256(password, salt, 200_000 iters)
Master key (32 bytes)
     │
     ▼  AES-256-GCM
Keystore file (~/.scs_keystore / ./keystore.enc)
     │  {
     │    "alice_rsa_private": "<AES-GCM-encrypted PEM>",
     │    "alice_rsa_public":  "<plaintext PEM>",
     │    ...
     │  }
```

Public keys are stored plaintext; only private keys are encrypted. Each entry uses its own nonce.

---

## 6. Authentication Flow

```
Registration
  user → register(username, password)
       → salt = os.urandom(16)
       → hashed = PBKDF2(password, salt, 200_000)
       → store (username, salt, hashed) in users.json (no plaintext passwords)

Login
  user → login(username, password)
       → load (salt, hashed) for username
       → candidate = PBKDF2(password, salt, 200_000)
       → constant_time_compare(candidate, hashed)  →  pass/fail
       → on pass: issue session token signed with server RSA private key
       → on fail: increment failure counter; lock after 5 failures
```

---

## 7. Thread Model

- **Server** runs one listener thread + one handler thread per connected client.
- **`EncryptionWorker`** (from spec skeleton) is implemented and available in `src/crypto/block_cipher.py` to meet the specification requirements. However, to simplify the chat pipeline and reduce thread overhead, the current implementation uses direct synchronous function calls for encryption and decryption rather than routing messages through the worker's queues.
- Synchronization is handled via threading Locks where necessary (e.g. for the clients dictionary).
