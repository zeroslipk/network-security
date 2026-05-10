"""
CLI entry point: python -m src.cli.main <command> [options]

Commands:
  server   --port PORT [--host HOST] [--db PATH]
  register --user USER --server HOST:PORT [--db PATH]
  chat     --user USER --server HOST:PORT [--db PATH]
"""

import argparse
import getpass
import sys

from src.net.client import ChatClient, register_remote
from src.net.server import ChatServer

DEFAULT_DB = "users.json"


def _parse_addr(addr: str) -> tuple[str, int]:
    host, port = addr.rsplit(':', 1)
    return host, int(port)


def cmd_server(args) -> None:
    srv = ChatServer(args.host, args.port, args.db)
    srv.start()


def cmd_register(args) -> None:
    host, port = _parse_addr(args.server)
    password = getpass.getpass(f"Choose password for {args.user}: ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("Passwords do not match.", file=sys.stderr)
        sys.exit(1)
    try:
        register_remote(host, port, args.user, password)
        print(f"User '{args.user}' registered on {args.server}.")
    except (ValueError, ConnectionError, OSError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_chat(args) -> None:
    host, port = _parse_addr(args.server)
    password = getpass.getpass(f"Password for {args.user}: ")
    client = ChatClient(host, port, args.user)
    try:
        client.connect(password)
    except (PermissionError, ConnectionError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    client.start_receive_thread(lambda msg: print(f"\r{msg}\n> ", end='', flush=True))
    try:
        while True:
            text = input('> ')
            if text:
                client.send(text)
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        client.close()
        print("\nDisconnected.")


def main():
    parser = argparse.ArgumentParser(description="Secure Communication Suite")
    sub = parser.add_subparsers(dest='command')

    p_server = sub.add_parser('server', help='Start the chat server')
    p_server.add_argument('--host', default='0.0.0.0')
    p_server.add_argument('--port', type=int, default=9000)
    p_server.add_argument('--db', default=DEFAULT_DB)

    p_reg = sub.add_parser('register', help='Register a new user on the server')
    p_reg.add_argument('--user', required=True)
    p_reg.add_argument('--server', default='localhost:9000')

    p_chat = sub.add_parser('chat', help='Start a chat session')
    p_chat.add_argument('--user', required=True)
    p_chat.add_argument('--server', default='localhost:9000')

    args = parser.parse_args()
    if args.command == 'server':
        cmd_server(args)
    elif args.command == 'register':
        cmd_register(args)
    elif args.command == 'chat':
        cmd_chat(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
