from __future__ import annotations

import importlib
import logging
import sys
from pathlib import Path


def _normalize_root(root_path: str | Path) -> Path:
    return Path(root_path).expanduser().resolve()


def _normalize_module_file(module_file: str | Path | None) -> Path | None:
    if not module_file:
        return None
    try:
        path = Path(module_file)
        if path.name.endswith(('.pyc', '.pyo')) and path.stem == '__init__':
            path = path.with_suffix('.py')
        elif path.suffix in {'.pyc', '.pyo'}:
            path = path.with_suffix('.py')
        return path.expanduser().resolve()
    except Exception:
        return None


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def collect_modules_under(root_path: Union[str, Path]) -> list[str]:
    root = _normalize_root(root_path)
    names: list[str] = []

    for name, module in list(sys.modules.items()):
        if not module or name.startswith("host"):
            continue

        module_file = getattr(module, '__file__', None)
        module_path = _normalize_module_file(module_file)
        if module_path is None:
            continue

        if _is_relative_to(module_path, root):
            names.append(name)

    return names


def purge_modules_under(root_path: Union[str, Path]) -> list[str]:
    root = _normalize_root(root_path)
    importlib.invalidate_caches()

    removed: list[str] = []
    for name in collect_modules_under(root):
        if sys.modules.pop(name, None) is not None:
            removed.append(name)

    for entry in list(sys.path_importer_cache.keys()):
        try:
            entry_path = Path(entry).expanduser().resolve()
        except Exception:
            continue
        if _is_relative_to(entry_path, root):
            sys.path_importer_cache.pop(entry, None)

    logging.info('DEV_CLEAN root=%s removed=%s', root, len(removed))
    return removed
