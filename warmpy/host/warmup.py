from __future__ import annotations

import importlib
import json
import logging
import time

from .paths import resource_path


def load_warmup_modules() -> list[str]:
    path = resource_path("warmup.json")
    if not path.exists():
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        logging.exception("WARMUP failed to read metadata path=%s", path)
        return []

    modules = data.get("modules") or []
    if isinstance(modules, str):
        modules = [modules]
    if not isinstance(modules, list):
        logging.error("WARMUP invalid metadata path=%s", path)
        return []

    return [m.strip() for m in modules if isinstance(m, str) and m.strip()]


def warmup() -> None:
    modules = load_warmup_modules()
    if not modules:
        logging.info("WARMUP skip (empty or missing)")
        return

    logging.info("WARMUP start n=%d", len(modules))
    for name in modules:
        t0 = time.perf_counter()
        ok = True
        err = None
        try:
            importlib.import_module(name)
        except Exception as e:
            ok = False
            err = repr(e)
            logging.exception("WARMUP import fail module=%s", name)
        ms = int((time.perf_counter() - t0) * 1000)
        logging.info("WARMUP module=%s ok=%s ms=%s err=%s", name, ok, ms, err)
