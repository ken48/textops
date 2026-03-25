#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import socket
import sys
from pathlib import Path

SOCKET_PATH = Path.home() / ".warmpy" / "warmpy.sock"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="warmpyctl",
        description="Send a script execution request to WarmPy.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clear user modules under clean root before running the script.",
    )
    parser.add_argument(
        "--clean-root",
        help="Root directory for module cleanup in --clean mode. "
        "Defaults to the script directory.",
    )
    parser.add_argument(
        "script",
        help="Path to the Python script to run.",
    )
    parser.add_argument(
        "script_args",
        nargs=argparse.REMAINDER,
        help="Arguments passed to the script.",
    )
    return parser


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.script_args and args.script_args[0] == "--":
        args.script_args = args.script_args[1:]

    return args


def build_payload(args: argparse.Namespace) -> bytes:
    script_path = Path(args.script).expanduser().resolve()

    payload = {
        "script": str(script_path),
        "args": list(args.script_args),
        "clean": bool(args.clean),
        "clean_root": (
            str(Path(args.clean_root).expanduser().resolve())
            if args.clean_root
            else None
        ),
    }
    return json.dumps(payload).encode("utf-8")


def send_payload(payload: bytes, args: argparse.Namespace) -> int:
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.connect(str(SOCKET_PATH))
            sock.sendall(payload)
        clean_suffix = ""
        if args.clean:
            clean_root = (
                Path(args.clean_root).expanduser().resolve()
                if args.clean_root
                else Path(args.script).expanduser().resolve().parent
            )
            clean_suffix = f" clean=True clean_root={clean_root}"

        print(
            f"WarmPy request sent: script={Path(args.script).expanduser().resolve()} "
            f"args={list(args.script_args)}{clean_suffix}"
        )
        return 0
    except FileNotFoundError:
        print(f"WarmPy socket not found: {SOCKET_PATH}", file=sys.stderr)
        return 1
    except ConnectionRefusedError:
        print(f"WarmPy is not accepting connections: {SOCKET_PATH}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"Failed to send request to WarmPy: {exc}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    payload = build_payload(args)
    return send_payload(payload, args)


if __name__ == "__main__":
    raise SystemExit(main())
