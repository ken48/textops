from __future__ import annotations

import os
import shlex
import subprocess
import sys
from pathlib import Path


def bundled_app_path(executable: Path | None = None) -> Path | None:
    resolved_executable = Path(sys.executable if executable is None else executable).resolve()

    if resolved_executable.parent.name != "MacOS":
        return None

    contents_dir = resolved_executable.parent.parent
    if contents_dir.name != "Contents":
        return None

    app_path = contents_dir.parent
    if app_path.suffix != ".app":
        return None

    return app_path


def relaunch_command(executable: Path | None = None) -> list[str] | None:
    app_path = bundled_app_path(executable)
    if app_path is not None:
        return ["/usr/bin/open", "-n", str(app_path)]

    return None


def schedule_relaunch(command: list[str] | None = None, *, pid: int | None = None) -> bool:
    effective_command = relaunch_command() if command is None else command
    if not effective_command:
        return False

    current_pid = os.getpid() if pid is None else pid
    quoted_command = " ".join(shlex.quote(part) for part in effective_command)
    helper_script = (
        f"while kill -0 {current_pid} 2>/dev/null; do sleep 0.1; done\n"
        f"exec {quoted_command}\n"
    )

    subprocess.Popen(
        ["/bin/sh", "-c", helper_script],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        close_fds=True,
    )
    return True
