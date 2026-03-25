from .encoding_setup import ensure_utf8_locale
from .logging_setup import setup_logging
from .socket_server import SocketServer
from .worker import Worker
from .menubar import run_app
from .warmup import warmup


def main() -> None:
    ensure_utf8_locale()
    worker = Worker()
    server = SocketServer(worker)
    if not server.reserve():
        return

    setup_logging()
    # Import heavy deps once to avoid first-run latency.
    # Scripts themselves are NOT imported/executed here.
    warmup()

    run_app(worker, server)
