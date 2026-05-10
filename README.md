# Secure Communication Suite

CSE451 Computer & Network Security — Ain Shams University, CHEP Spring 2026

A Python application implementing AES-256-GCM symmetric encryption, RSA-2048 asymmetric encryption, SHA-256 hashing (from scratch), PBKDF2 key derivation, secure key management, password-based authentication, and a secure TCP chat as the internet-services demo.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run the secure chat

### CLI

**Terminal 1 — server:**
```bash
python -m src.cli.main server --port 9000
```

**Terminals 2 & 3 — register and chat:**
```bash
python -m src.cli.main register --user alice --server localhost:9000
python -m src.cli.main chat     --user alice --server localhost:9000

python -m src.cli.main register --user bob   --server localhost:9000
python -m src.cli.main chat     --user bob   --server localhost:9000
```

Registration is performed over the network — the client never needs filesystem access to the server.

### GUI

```bash
python -m src.gui.app --server localhost:9000
```

Tkinter window with login/register fields. On successful login, transitions to a chat window with a scrollable message log and input box. Run multiple instances side-by-side to chat between users.

## Run tests

```bash
pytest tests/ -v
```

## Project structure

```
src/
  crypto/         # block_cipher, public_key, hashing (scratch), kdf (scratch)
  keymgmt/        # keystore, key_exchange
  auth/           # password_auth, session
  net/            # protocol, server, client
  cli/            # main entry point
tests/            # unit + integration tests
docs/             # SRS, design, threat model, report
demos/            # eavesdrop, tamper, replay demonstration scripts
```

## Cryptographic algorithms

| Layer | Algorithm | Mode | Key size |
|---|---|---|---|
| Symmetric encryption | AES | GCM | 256-bit |
| Asymmetric encryption | RSA | OAEP (encrypt) / PSS (sign) | 2048-bit |
| Hashing | SHA-256 | — | 256-bit output |
| MAC | HMAC | SHA-256 | session key |
| Key derivation | PBKDF2 | HMAC-SHA256 | 200 000 iterations |

SHA-256, HMAC, and PBKDF2 are implemented from scratch per FIPS 180-4 and RFC 8018.



















Plan — fix the three grading-impact gaps
Gap 1: Wire the from-scratch PBKDF2 into actual code paths
Files: src/auth/password_auth.py, src/keymgmt/keystore.py

In both files, replace the local hashlib-backed pbkdf2 with from src.crypto.kdf import pbkdf2.
Drop the import hashlib line.
Decision needed: existing users.json was hashed via stdlib PBKDF2 — output is byte-identical to ours, so existing accounts will still log in. Test this; if it doesn't, just delete users.json and re-register.
Verify: pytest tests/test_auth.py tests/test_kdf.py tests/test_keymgmt.py -v all pass; grep confirms no hashlib import remains in src/auth/ or src/keymgmt/.

Gap 2: Fix the handshake MITM
Files: src/net/server.py, src/net/client.py, new server_pub.pem

Pick one approach:

Option	Effort	Effect
A. Pin server pubkey (recommended)	~30 min	Server persists its keypair to disk on first start; client ships with server_pub.pem and rejects mismatched SERVER_HELLO. Closest to TLS cert pinning — easy to explain in the report.
B. Trust-on-first-use (TOFU)	~20 min	Client stores fingerprint on first connect, warns on change. Weaker but easy.
C. Document as known limitation	~5 min	Just update docs/threat_model.md. Honest but loses marks if examiner probes.
Plan for A:

In ChatServer.__init__, load server_key.pem/server_pub.pem from disk; if absent, generate_keypair() and write both. Add --keydir flag.
In ChatClient.__init__, accept expected_server_pub: bytes (load from server_pub.pem).
In connect(), after receiving SERVER_HELLO, compare with hmac.compare_digest; raise ConnectionError("Server identity mismatch") on mismatch.
Update CLI (src/cli/main.py) and GUI (src/gui/login_win.py) to pass the pinned key.
Add a test: spin up a server with key A, point a client expecting key B → expect ConnectionError.
Verify: new test passes; existing integration tests still pass; manual chat between alice/bob still works.

Gap 3: Remove committed user database
Files: users.json, .gitignore

rm users.json
Create .gitignore with users.json, server_key.pem, __pycache__/, .pytest_cache/, venv/.
Confirm password_auth.register() creates the file fresh on first user (it does — password_auth.py:24).
Verify: git status shows users.json ignored; python -m src.cli.main register from a clean dir creates a valid DB.

Suggested order & time
Gap 3 (5 min) — quick win, makes Gap 1 testing cleaner.
Gap 1 (15 min) — small, isolated.
Gap 2 option A (45 min) — bigger, do after the easy ones land.
Run full pytest + both smoke scripts, save output for the report's Phase 4 "test results" section.
Total: ~1.5 hours of work plus a final verification pass.

Want me to start executing, or wait for your go-ahead on the MITM approach (A vs B vs C)?

