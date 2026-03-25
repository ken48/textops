from __future__ import annotations

import json
import atexit
import logging
import socket
import sys
import threading
from datetime import datetime
from typing import Any, List, Optional, Tuple

from .paths import START_ATTEMPTS_DIR, WARMPY_DIR, SOCKET_PATH

ParsedRequest = Tuple[str, List[str], bool, Optional[str]]


class SocketServer:
    def __init__(self, worker: Any) -> None:
        self.worker = worker
        self._stop = threading.Event()
        self._sock: socket.socket | None = None
        self._listen_t = threading.Thread(
            target=self._listen_loop, name="warmpy-sock-listen", daemon=True
        )

    def reserve(self) -> bool:
        WARMPY_DIR.mkdir(parents=True, exist_ok=True)
        try:
            if SOCKET_PATH.exists():
                if self._is_server_alive():
                    self._write_start_attempt("already-running", f"socket already active: {SOCKET_PATH}")
                    return False
                SOCKET_PATH.unlink()
        except Exception:
            self._write_start_attempt("socket-unlink-failed", f"socket unlink failed: {SOCKET_PATH}")
            return False

        try:
            self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self._sock.bind(str(SOCKET_PATH))
        except Exception:
            self._write_start_attempt("socket-bind-failed", f"socket bind/listen failed: {SOCKET_PATH}")
            try:
                if self._sock is not None:
                    self._sock.close()
            except Exception:
                pass
            self._sock = None
            return False

        atexit.register(self._cleanup)
        return True

    def start(self) -> bool:
        if self._sock is None:
            return False
        self._sock.listen(5)
        self._listen_t.start()
        logging.info("SOCKET started path=%s", SOCKET_PATH)
        return True

    def _write_start_attempt(self, reason: str, message: str) -> None:
        try:
            START_ATTEMPTS_DIR.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S-%f")[:-3]
            path = START_ATTEMPTS_DIR / f"{stamp}-{reason}.log"
            path.write_text(
                f"time={stamp}\nreason={reason}\nmessage={message}\nsocket={SOCKET_PATH}\n",
                encoding="utf-8",
            )
        except Exception:
            print(f"warmpy start-attempt logging failed: reason={reason}", file=sys.stderr)

    def _cleanup(self) -> None:
        try:
            if self._sock is not None:
                self._sock.close()
                self._sock = None
        except Exception:
            pass
        try:
            if SOCKET_PATH.exists():
                SOCKET_PATH.unlink()
        except Exception:
            pass

    def _is_server_alive(self) -> bool:
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as probe:
                probe.connect(str(SOCKET_PATH))
            return True
        except OSError:
            return False

    def _read_request(self, conn: socket.socket) -> str | None:
        """Read raw bytes from connection. Returns decoded text or None on error."""
        conn.settimeout(5.0)
        chunks = []
        total = 0
        limit = 1024 * 1024
        while True:
            chunk = conn.recv(65536)
            if not chunk:
                break
            total += len(chunk)
            if total > limit:
                logging.error("SOCKET payload exceeds %d bytes, dropping", limit)
                return None
            chunks.append(chunk)
        data = b"".join(chunks)
        if not data:
            return None
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError as e:
            logging.error("SOCKET payload decode failed: %s", e)
            return None

    def _parse_request(self, payload_text: str) -> ParsedRequest | None:
        """Parse payload into (script, args, clean, clean_root). Returns None on error."""
        if payload_text.lstrip().startswith("{"):
            try:
                payload = json.loads(payload_text)
            except json.JSONDecodeError as e:
                logging.error("SOCKET payload JSON parse failed: %s", e)
                return None
            if not isinstance(payload, dict):
                logging.error("SOCKET payload must be a JSON object")
                return None
            raw_args = payload.get("args", [])
            raw_clean_root = payload.get("clean_root")
            if not isinstance(raw_args, list):
                logging.error("SOCKET payload field 'args' must be a list, got %s", type(raw_args).__name__)
                return None
            if raw_clean_root is not None and not isinstance(raw_clean_root, str):
                logging.error("SOCKET payload field 'clean_root' must be a string, got %s", type(raw_clean_root).__name__)
                return None
            raw_clean = payload.get("clean", False)
            if not isinstance(raw_clean, bool):
                logging.error("SOCKET payload field 'clean' must be a boolean, got %s", type(raw_clean).__name__)
                return None
            return (
                str(payload.get("script", "")).strip(),
                [str(p) for p in raw_args],
                raw_clean,
                raw_clean_root,
            )
        else:
            parts = payload_text.split("\x00")
            return parts[0].strip(), [p for p in parts[1:] if p != ""], False, None

    def _handle_connection(self, conn: socket.socket) -> None:
        """Handle a single accepted connection."""
        payload_text = self._read_request(conn)
        if payload_text is None:
            return
        result = self._parse_request(payload_text)
        if result is None:
            return
        script, args, clean, clean_root = result
        if script:
            self.worker.run_script(script, args, clean=clean, clean_root=clean_root)

    def _listen_loop(self) -> None:
        s = self._sock
        if s is None:
            return
        try:
            while not self._stop.is_set():
                try:
                    conn, _ = s.accept()
                except Exception:
                    continue
                try:
                    self._handle_connection(conn)
                except Exception:
                    logging.exception("SOCKET handle failed")
                finally:
                    try:
                        conn.close()
                    except Exception:
                        pass
        except Exception:
            logging.exception("SOCKET listen failed path=%s", SOCKET_PATH)
        finally:
            try:
                s.close()
            except Exception:
                pass
