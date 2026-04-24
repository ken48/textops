import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "warmpy"))

from host.relaunch import bundled_app_path, relaunch_command


class RelaunchTests(unittest.TestCase):
    def test_detects_bundled_app_path_from_macos_executable(self) -> None:
        executable = Path("/Applications/warmpy.app/Contents/MacOS/warmpy")

        self.assertEqual(
            bundled_app_path(executable),
            Path("/Applications/warmpy.app"),
        )

    def test_returns_none_for_non_bundle_executable(self) -> None:
        executable = Path("/usr/local/bin/python3")

        self.assertIsNone(bundled_app_path(executable))

    def test_uses_open_for_bundled_relaunch(self) -> None:
        executable = Path("/Applications/warmpy.app/Contents/MacOS/warmpy")

        self.assertEqual(
            relaunch_command(executable),
            ["/usr/bin/open", "-n", "/Applications/warmpy.app"],
        )

    def test_returns_none_for_non_bundle_relaunch(self) -> None:
        executable = Path("/usr/local/bin/python3")

        self.assertIsNone(relaunch_command(executable))


if __name__ == "__main__":
    unittest.main()
