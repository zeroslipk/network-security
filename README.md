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



















Plan — fix the three grading-impact gaps (✅ All gaps resolved)
✅ Gap 1: Wire the from-scratch PBKDF2 into actual code paths
Files: src/auth/password_auth.py, src/keymgmt/keystore.py
- Hashlib successfully removed, custom PBKDF2 wired up.

✅ Gap 2: Fix the handshake MITM
Files: src/net/server.py, src/net/client.py
- Trust-On-First-Use (TOFU) key pinning implemented. `pinned_server_pub.pem` verifies identity.

✅ Gap 3: Remove committed user database
Files: users.json, .gitignore
- `users.json`, server keys, and venv successfully added to `.gitignore` and removed from tracking.

All pending security and grading gaps have been addressed and the demo scripts execute perfectly.

