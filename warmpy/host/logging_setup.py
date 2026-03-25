import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .paths import WARMPY_DIR, LOG_FILE

LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 3


def setup_logging() -> Path:
    """Configure logging to ~/.warmpy/warmpy.log."""
    WARMPY_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8"):
        pass

    handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)

    logging.info("=== WarmPy started ===")
    logging.info("LOG path=%s", LOG_FILE)
    logging.info(
        "LOG rotation max_bytes=%s backups=%s",
        LOG_MAX_BYTES,
        LOG_BACKUP_COUNT,
    )
    return LOG_FILE
