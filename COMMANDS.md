# Commands

Quick reference for running and testing the Secure Communication Suite.

## Setup (once)

```bash
pip3 install -r requirements.txt
```

## Run the tests

```bash
# Full suite (59 tests)
python3 -m pytest tests/ -v --timeout=30

# Single module
python3 -m pytest tests/test_hashing.py -v
```

## Run the smoke tests

```bash
# CLI end-to-end (registration, login, chat, lockout, tamper detection)
python3 scripts/smoke_test.py

# GUI headless (drives the Tk windows programmatically)
python3 scripts/gui_smoke_test.py
```

## Run the chat server

```bash
python3 -m src.cli.main server --port 9000
```

## Use the CLI client

```bash
# Register a new user
python3 -m src.cli.main register --user alice --server localhost:9000

# Start chatting
python3 -m src.cli.main chat --user alice --server localhost:9000
```

## Use the GUI client

```bash
python3 -m src.gui.app --server localhost:9000
```

Login window opens — enter username/password, click **Register** for new users (wait for the green status), then click **Login**.

## Reset the user database

```bash
rm users.json
```
