from __future__ import annotations

import logging
import runpy
import sys
import threading
import time
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any, Callable

from .dev_clean import purge_modules_under


class _LogStream:
    def __init__(self, prefix: str, level: int) -> None:
        self.prefix = prefix
        self.level = level
        self._buffer = ""

    def write(self, data: object) -> int:
        if not data:
            return 0
        self._buffer += str(data)
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            self._log(line)
        return len(data)

    def flush(self) -> None:
        if self._buffer:
            self._log(self._buffer)
            self._buffer = ""

    def _log(self, line: str) -> None:
        logging.log(self.level, "%s %s", self.prefix, line)


class Worker:
    """Minimal single-process runner (TCC-friendly .app wrapper).

    - No engine subprocess.
    - No queue: if busy -> drop.
    - Scripts are plain Python files; host executes them as __main__.
    - Warmup happens via metadata (see host.warmup).
    - Accepts an absolute/relative path to a .py file.
    """

    def __init__(self) -> None:
        # Single-flight guard for script execution. The socket listener acquires it
        # before handing work to the main thread; _run_job() must release it.
        self._run_lock = threading.Lock()
        self._dispatch_to_main: Callable[[dict[str, Any]], None] | None = None

    def attach_main_thread_dispatcher(self, dispatcher: Callable[[dict[str, Any]], None]) -> None:
        self._dispatch_to_main = dispatcher

    def run_script(
        self,
        script_path: str,
        args: list[str] | None = None,
        clean: bool = False,
        clean_root: str | None = None,
    ) -> bool:
        effective_args = [] if args is None else list(args)

        if not self._run_lock.acquire(blocking=False):
            logging.warning("DROP busy script=%s args=%s", script_path, effective_args)
            return False

        path = Path(script_path).expanduser().resolve()

        if path.suffix.lower() != ".py":
            logging.error("REJECT not a .py file: %s", path)
            self._run_lock.release()
            return False

        if not path.exists() or not path.is_file():
            logging.error("MISSING script=%s", path)
            self._run_lock.release()
            return False

        effective_clean_root = Path(clean_root).expanduser().resolve() if clean_root else path.parent

        logging.info(
            "ACCEPT script=%s args=%s clean=%s clean_root=%s",
            path,
            effective_args,
            clean,
            effective_clean_root,
        )

        if self._dispatch_to_main is None:
            logging.error("RUNNER missing main-thread bridge")
            self._run_lock.release()
            return False

        job = {
            "path": path,
            "args": effective_args,
            "clean": clean,
            "clean_root": effective_clean_root,
        }

        # Keep the lock held across the socket-thread -> main-thread handoff so
        # overlapping requests are rejected until the current script fully ends.
        try:
            self._dispatch_to_main(job)
        except Exception:
            logging.exception("RUNNER dispatch failed script=%s", path)
            self._run_lock.release()
            return False

        return True

    def _run_job(self, job: dict[str, Any]) -> None:
        # This method owns releasing _run_lock for every accepted job.
        path = job["path"]
        args = job["args"]
        clean = job["clean"]
        effective_clean_root = job["clean_root"]

        t0 = time.perf_counter()
        ok = True
        err = None
        old_argv = sys.argv
        # Temporarily add the script directory to sys.path for sibling imports
        script_dir = str(path.parent)
        added = False
        try:
            if script_dir and script_dir not in sys.path:
                sys.path.insert(0, script_dir)
                added = True

            if clean:
                purge_modules_under(effective_clean_root)

            sys.argv = [str(path), *args]
            logging.info("RUN begin script=%s", path)
            stdout_stream = _LogStream("STDOUT", logging.INFO)
            stderr_stream = _LogStream("STDERR", logging.ERROR)
            with redirect_stdout(stdout_stream), redirect_stderr(stderr_stream):
                runpy.run_path(str(path), run_name="__main__")
            stdout_stream.flush()
            stderr_stream.flush()
            logging.info("RUN end script=%s", path)
        except Exception as e:
            ok = False
            err = repr(e)
            logging.exception("FAIL script=%s", path)
        finally:
            sys.argv = old_argv
            if added:
                try:
                    sys.path.remove(script_dir)
                except ValueError:
                    pass
            ms = int((time.perf_counter() - t0) * 1000)
            logging.info(
                "DONE script=%s ok=%s ms=%s err=%s",
                path,
                ok,
                ms,
                err,
            )
            self._run_lock.release()
