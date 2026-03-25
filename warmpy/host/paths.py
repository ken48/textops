import sys
from pathlib import Path

# Runtime directory for socket + logs (no config/pid)
WARMPY_DIR = Path.home() / ".warmpy"
START_ATTEMPTS_DIR = WARMPY_DIR / "start-attempts"

SOCKET_PATH = WARMPY_DIR / "warmpy.sock"
LOG_FILE = WARMPY_DIR / "warmpy.log"


def resource_path(filename: str) -> Path:
    """Resolve a bundled resource path, with development fallbacks."""
    exe = Path(sys.executable).resolve()
    bundled = exe.parents[1] / "Resources" / filename
    if bundled.exists():
        return bundled

    project_root = Path(__file__).resolve().parent.parent
    assets_path = project_root / "assets" / filename
    if assets_path.exists():
        return assets_path

    return project_root / ".build" / filename
