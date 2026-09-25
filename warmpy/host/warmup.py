from __future__ import annotations

import importlib
import json
import logging
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

from .paths import resource_path


@dataclass(frozen=True)
class WarmupConfig:
    modules: tuple[str, ...]
    prewarm_modules: tuple[str, ...]
    prewarm_paths: tuple[str, ...]


def _string_list(data: dict[str, object], key: str) -> tuple[str, ...]:
    values = data.get(key) or []
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, list):
        logging.error("WARMUP invalid metadata field=%s", key)
        return ()
    return tuple(
        value.strip()
        for value in values
        if isinstance(value, str) and value.strip()
    )


def load_warmup_config() -> WarmupConfig:
    path = resource_path("warmup.json")
    if not path.exists():
        return WarmupConfig((), (), ())

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        logging.exception("WARMUP failed to read metadata path=%s", path)
        return WarmupConfig((), (), ())

    if not isinstance(data, dict):
        logging.error("WARMUP invalid metadata path=%s", path)
        return WarmupConfig((), (), ())

    return WarmupConfig(
        modules=_string_list(data, "modules"),
        prewarm_modules=_string_list(data, "prewarm_modules"),
        prewarm_paths=_string_list(data, "prewarm_paths"),
    )


def load_warmup_modules() -> list[str]:
    """Return import-only modules for compatibility with older callers."""
    return list(load_warmup_config().modules)


@contextmanager
def _temporary_import_paths(paths: tuple[str, ...]) -> Iterator[None]:
    added: list[str] = []
    for raw_path in reversed(paths):
        path = str(Path(raw_path).expanduser().resolve())
        if path not in sys.path:
            sys.path.insert(0, path)
            added.append(path)

    try:
        yield
    finally:
        for path in added:
            try:
                sys.path.remove(path)
            except ValueError:
                pass


def _import_module(name: str, log_prefix: str) -> ModuleType | None:
    t0 = time.perf_counter()
    ok = True
    err = None
    module = None
    try:
        module = importlib.import_module(name)
    except Exception as exc:
        ok = False
        err = repr(exc)
        logging.exception("%s import fail module=%s", log_prefix, name)
    ms = int((time.perf_counter() - t0) * 1000)
    logging.info("%s module=%s ok=%s ms=%s err=%s", log_prefix, name, ok, ms, err)
    return module


def _run_prewarm(name: str) -> None:
    t0 = time.perf_counter()
    ok = True
    err = None
    try:
        module = importlib.import_module(name)
        prewarm = getattr(module, "prewarm", None)
        if not callable(prewarm):
            raise AttributeError(f"module {name!r} has no callable prewarm()")
        prewarm()
    except Exception as exc:
        ok = False
        err = repr(exc)
        logging.exception("PREWARM failed module=%s", name)
    ms = int((time.perf_counter() - t0) * 1000)
    logging.info("PREWARM module=%s ok=%s ms=%s err=%s", name, ok, ms, err)


def warmup() -> None:
    config = load_warmup_config()
    if not config.modules and not config.prewarm_modules:
        logging.info("WARMUP skip (empty or missing)")
        return

    logging.info("WARMUP start n=%d", len(config.modules))
    for name in config.modules:
        _import_module(name, "WARMUP")

    logging.info("PREWARM start n=%d", len(config.prewarm_modules))
    with _temporary_import_paths(config.prewarm_paths):
        for name in config.prewarm_modules:
            _run_prewarm(name)
