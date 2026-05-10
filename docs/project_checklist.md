# CSE451 Project Specification — Compliance Checklist

> Based on the specification PDF and full codebase review.  
> ✅ = Done · ⚠️ = Partial / Has Issues · ❌ = Missing

---

## Phase 1 — Core Cryptographic Modules

### 1. Block Cipher Module (`src/crypto/block_cipher.py`)

| # | Requirement | Status | Evidence |
|---|---|---|---|
| BC-1 | AES-256-GCM encrypt → `(nonce, ciphertext, tag)` | ✅ | `encrypt()` uses `AES.MODE_GCM`, 12-byte nonce, 256-bit key |
| BC-2 | AES-256-GCM decrypt and verify tag | ✅ | `decrypt()` calls `decrypt_and_verify()` |
| BC-3 | Raise exception on tag verification failure (no partial plaintext) | ✅ | PyCryptodome raises `ValueError` internally |
| BC-4 | `EncryptionWorker` thread from spec skeleton (queue-based) | ✅ | `EncryptionWorker(Thread)` reads from `plaintext_queue`, writes to `ciphertext_queue` |
| BC-5 | 256-bit key generation via CSPRNG | ✅ | `generate_key()` → `os.urandom(32)` |

### 2. Public Key Cryptosystem Module (`src/crypto/public_key.py`)

| # | Requirement | Status | Evidence |
|---|---|---|---|
| PK-1 | RSA-2048 key pair generation | ✅ | `RSA.generate(2048)` |
| PK-2 | PEM export/import of public and private keys | ✅ | `export_key()`, `import_key()` wrappers |
| PK-3 | RSA-OAEP encrypt with SHA-256 | ✅ | `PKCS1_OAEP.new(key, hashAlgo=SHA256)` |
| PK-4 | RSA-OAEP decrypt | ✅ | Same, with private key |
| PK-5 | RSA-PSS sign | ✅ | `pss.new(key).sign(h)` |
| PK-6 | RSA-PSS verify → `True`/`False` | ✅ | Returns bool, catches `ValueError`/`TypeError` |

### 3. Hashing Module (`src/crypto/hashing.py` + `src/crypto/kdf.py`)

| # | Requirement | Status | Evidence |
|---|---|---|---|
| H-1 | SHA-256 from scratch (FIPS 180-4), no `hashlib` | ✅ | Full implementation with constants, compression, padding |
| H-2 | Passes NIST SHA-256 Known Answer Test vectors | ✅ | `test_hashing.py::test_nist_vectors` — 4 KAT vectors |
| H-3 | HMAC-SHA256 from scratch (RFC 2104) using our SHA-256 | ✅ | `hmac_sha256()` with proper ipad/opad |
| H-4 | PBKDF2-HMAC-SHA256 from scratch (RFC 8018) using our HMAC | ✅ | `kdf.py::pbkdf2()` — salt+block concat, XOR chain |

### 4. Key Management Module (`src/keymgmt/`)

| # | Requirement | Status | Evidence |
|---|---|---|---|
| KM-1 | Store named key in AES-GCM encrypted keystore file | ✅ | `keystore.py::save_key()` |
| KM-2 | Load named key; fail on wrong password | ✅ | `load_key()` → `_open_keystore()` verifies via decryption |
| KM-3 | List all key names | ✅ | `list_keys()` |
| KM-4 | Delete a key from the keystore | ✅ | `delete_key()` |
| KM-5 | Keystore master key derived via PBKDF2 | ⚠️ | **Uses `hashlib.pbkdf2_hmac` instead of the from-scratch `kdf.pbkdf2`** — see Gap 1 below |
| KM-6 | RSA-OAEP wrapping of AES session key | ✅ | `key_exchange.py::wrap_session_key()` |
| KM-7 | RSA-OAEP unwrapping of session key | ✅ | `key_exchange.py::unwrap_session_key()` |

### 5. Authentication Module (`src/auth/`)

| # | Requirement | Status | Evidence |
|---|---|---|---|
| AU-1 | Register user with `(username, salt, PBKDF2(pw, salt, 200k))` | ⚠️ | Works, but **uses `hashlib.pbkdf2_hmac` instead of from-scratch** — see Gap 1 below |
| AU-2 | Login with constant-time comparison | ✅ | `hmac.compare_digest()` on line 68 |
| AU-3 | Lockout after 5 consecutive failures | ✅ | `_MAX_FAILURES = 5`, sets `locked = True` |
| AU-4 | Issue signed session token `{username, expiry, nonce}` | ✅ | `session.py::issue_token()` — RSA-PSS signed JSON |
| AU-5 | Verify session token signature + expiry | ✅ | `session.py::verify_token()` |

### 6. Internet Services Security Module (Secure Chat)

| # | Requirement | Status | Evidence |
|---|---|---|---|
| IS-1 | TCP server, multiple clients via threads | ✅ | `server.py` — `srv.listen(10)`, thread per `_handle()` |
| IS-2 | Handshake: ClientHello → ServerHello → Login → AuthOK+SessionKey | ✅ | Full flow in `server.py::_handle()` and `client.py::connect()` |
| IS-3 | Post-handshake messages: AES-256-GCM + HMAC-SHA256 | ✅ | `protocol.py::send_frame()` / `recv_frame()` |
| IS-4 | Unique nonces per message; replay detection | ✅ | `seen_nonces` set in `recv_frame()` |
| IS-5 | CLI: `register`, `login`, `chat` commands | ✅ | `cli/main.py` — `server`, `register`, `chat` subcommands |
| IS-6 | GUI for the secure chat | ✅ | `src/gui/` — Tkinter login + chat windows (stretch goal achieved) |

---

## Phase 2 — Security Properties

| # | Requirement | Status | Evidence |
|---|---|---|---|
| NF-1 | Adequate key sizes: AES-256, RSA-2048 | ✅ | 32-byte keys, `RSA.generate(2048)` |
| NF-2 | Passwords never stored/transmitted in plaintext | ⚠️ | **Stored**: only PBKDF2 hash in `users.json` ✅. **Transmitted**: password sent as plaintext JSON in `LOGIN_REQUEST` and `REGISTER_REQUEST` ⚠️ — see Gap 5 below |
| NF-3 | PBKDF2 ≥ 200,000 iterations | ✅ | `_ITERATIONS = 200_000` in both auth and keystore |
| NF-4 | AES nonces via `os.urandom(12)`, never reused | ✅ | `os.urandom(12)` in `block_cipher.py` |
| NF-5 | Timing-safe comparison for passwords/MACs | ✅ | `hmac.compare_digest()` used in auth and protocol |
| NF-6 | Keystore file never has plaintext key material | ✅ | All keys AES-GCM encrypted before writing |
| NF-7 | Python 3.11+ on Linux/macOS/Windows | ✅ | Uses only stdlib + pycryptodome; type hints require 3.10+ |
| NF-8 | All modules include unit tests with KAT vectors | ✅ | 8 test files covering all modules |

---

## Phase 3 — Testing & Demonstration

| # | Requirement | Status | Evidence |
|---|---|---|---|
| T-1 | Unit tests for block cipher module | ✅ | `test_block_cipher.py` — 7 tests |
| T-2 | Unit tests for public key module | ✅ | `test_public_key.py` — 7 tests |
| T-3 | Unit tests for hashing module (NIST KAT) | ✅ | `test_hashing.py` — 7 tests incl. NIST vectors |
| T-4 | Unit tests for KDF module (RFC vectors) | ✅ | `test_kdf.py` — 4 tests incl. RFC 6070/hashlib cross-check |
| T-5 | Unit tests for key management | ✅ | `test_keymgmt.py` — 10 tests |
| T-6 | Unit tests for authentication | ✅ | `test_auth.py` — 10 tests |
| T-7 | Integration tests (end-to-end client↔server) | ✅ | `test_integration.py` — 6 tests |
| T-8 | Eavesdrop demo script | ❌ | `demos/eavesdrop.py` **does not exist** (dir is empty) — see Gap 3 below |
| T-9 | Tamper demo script | ❌ | `demos/tamper.py` **does not exist** — see Gap 3 below |
| T-10 | Replay demo script | ❌ | `demos/replay.py` **does not exist** — see Gap 3 below |
| T-11 | Smoke test (CLI end-to-end) | ✅ | `scripts/smoke_test.py` — 6 steps |
| T-12 | Smoke test (GUI) | ✅ | `scripts/gui_smoke_test.py` |

---

## Phase 4 — Documentation & Deliverables

| # | Requirement | Status | Evidence |
|---|---|---|---|
| D-1 | Software Requirements Specification (SRS) | ✅ | `docs/SRS.md` — 170 lines, well-structured |
| D-2 | Design Document (architecture, diagrams, protocols) | ✅ | `docs/design.md` — module diagram, wire frame, handshake, key mgmt |
| D-3 | Threat Model (STRIDE analysis, attack scenarios) | ✅ | `docs/threat_model.md` — STRIDE + 5 scenarios |
| D-4 | Final project report | ❌ | `docs/report/` **is empty** — see Gap 4 below |
| D-5 | README with setup/run instructions | ✅ | `README.md` — setup, CLI, GUI, tests, structure |
| D-6 | `.gitignore` to exclude sensitive files | ❌ | **No `.gitignore` file exists** — see Gap 6 below |
| D-7 | `users.json` NOT committed to repo | ❌ | **`users.json` is committed** with 4 user entries — see Gap 6 below |

---

## Critical Gaps Summary

---

### 🔴 Gap 1 — From-scratch PBKDF2 NOT wired into production code

**⚠️ GRADING-CRITICAL:** The from-scratch `src/crypto/kdf.py::pbkdf2()` exists and is tested, but **both `password_auth.py` and `keystore.py` still import `hashlib` and use `hashlib.pbkdf2_hmac()`** instead of the from-scratch implementation. The spec explicitly requires PBKDF2 to be implemented from scratch. An examiner checking `import hashlib` will flag this immediately.

**Files to fix:**
- `src/auth/password_auth.py` — `import hashlib` + `hashlib.pbkdf2_hmac` on L7, L15-16
- `src/keymgmt/keystore.py` — `import hashlib` + `hashlib.pbkdf2_hmac` on L7, L15-16

**Fix:** Replace both local `pbkdf2` functions with `from src.crypto.kdf import pbkdf2`.

---

### 🟡 Gap 2 — No MITM protection on handshake

The server generates a new RSA keypair on every restart (`__init__` calls `generate_keypair()`). The client blindly trusts whatever public key the `SERVER_HELLO` provides. No certificate pinning, TOFU, or PKI exists.

**Impact:** The threat model acknowledges this as a known limitation (see `docs/threat_model.md` line 110-112), which is honest — but the README mentions a plan to fix it (Option A: pin server pubkey). If the spec expects this, it's a gap.

**Fix:** Persist server keypair to disk on first start; distribute `server_pub.pem` to clients; reject mismatched `SERVER_HELLO`.

---

### 🔴 Gap 3 — Demo scripts are missing

The `demos/` directory is **completely empty**. The threat model references:
- `demos/eavesdrop.py` (Scenario 1)
- `demos/tamper.py` (Scenario 2)
- `demos/replay.py` (Scenario 3)

**Impact:** The spec requires demonstrating attack scenarios. Without these, the security demo portion is undeliverable.

**Fix:** Create all three scripts. The tamper and replay logic already exists in `smoke_test.py` and `test_integration.py` — extract and polish into standalone demos.

---

### 🔴 Gap 4 — Final project report is missing

The `docs/report/` directory is empty. The spec typically requires a comprehensive project report covering:
- Implementation details per phase
- Test results with screenshots/output
- Security analysis and STRIDE findings
- Known limitations and future work
- Team contributions

**Fix:** Write the report. Much of the content can be assembled from existing docs (SRS, design, threat model) + pytest output.

---

### 🟡 Gap 5 — Password sent in plaintext during login

During the handshake, `LOGIN_REQUEST` and `REGISTER_REQUEST` send the password as a plain JSON field **before** the session key is established. While this is over a raw TCP socket (no TLS), the password traverses the network unencrypted.

The design document (line 94-95) describes `RSA-PSS(PBKDF2(password))` in the `LoginRequest`, but the actual code just sends `{'password': password}` in plain JSON.

**Impact:** Contradicts NF-2 ("passwords never transmitted in plaintext") and the design document's claim.

**Fix:** Either hash the password client-side before sending, or encrypt the login message with the server's public key received in `SERVER_HELLO`.

---

### 🔴 Gap 6 — Committed `users.json` + no `.gitignore`

- `users.json` containing 4 user accounts is committed to the repo
- No `.gitignore` exists, meaning `__pycache__/`, `.pytest_cache/`, `venv/`, and sensitive files will all be tracked

**Fix:**
1. `rm users.json` (or `git rm`)
2. Create `.gitignore` with: `users.json`, `server_key.pem`, `server_pub.pem`, `*.ks`, `__pycache__/`, `.pytest_cache/`, `venv/`

---

### 🟡 Gap 7 — `EncryptionWorker` not actually used in the chat pipeline

The `EncryptionWorker` class exists in `block_cipher.py` and is unit-tested, but the actual `server.py` and `client.py` call `send_frame()` / `recv_frame()` directly — they don't route messages through `EncryptionWorker`'s queues. The design document (§7) claims the worker is used, but the code doesn't reflect this.

**Impact:** Minor — the spec only says to provide the class (which exists). But the design doc is inconsistent with the implementation.

---

## Priority Order for Fixes

| Priority | Gap | Effort | Impact |
|---|---|---|---|
| 1 | **Gap 6** — `.gitignore` + remove `users.json` | 5 min | Quick win, prevents data leak |
| 2 | **Gap 1** — Wire from-scratch PBKDF2 into auth & keystore | 15 min | **Grading-critical** — examiner will grep for `hashlib` |
| 3 | **Gap 3** — Create demo scripts | 45 min | **Deliverable** referenced in docs |
| 4 | **Gap 4** — Write final report | 2-3 hrs | **Required deliverable** |
| 5 | **Gap 5** — Hash/encrypt password before transmission | 30 min | Fixes spec compliance + design doc consistency |
| 6 | **Gap 2** — Server key pinning | 45 min | Strengthens security, already planned |
| 7 | **Gap 7** — Align design doc re: EncryptionWorker | 10 min | Documentation accuracy |
