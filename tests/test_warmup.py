from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import ModuleType
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "warmpy"))

from host import warmup


class WarmupConfigTests(unittest.TestCase):
    def test_loads_import_and_prewarm_metadata(self) -> None:
        with TemporaryDirectory() as directory:
            metadata_path = Path(directory) / "warmup.json"
            metadata_path.write_text(
                json.dumps(
                    {
                        "modules": ["dependency", ""],
                        "prewarm_modules": ["feature"],
                        "prewarm_paths": ["/project/scripts"],
                    }
                ),
                encoding="utf-8",
            )

            with patch.object(warmup, "resource_path", return_value=metadata_path):
                config = warmup.load_warmup_config()

        self.assertEqual(config.modules, ("dependency",))
        self.assertEqual(config.prewarm_modules, ("feature",))
        self.assertEqual(config.prewarm_paths, ("/project/scripts",))

    def test_calls_module_prewarm_and_restores_import_path(self) -> None:
        hook = Mock()
        module = ModuleType("feature")
        module.prewarm = hook
        config = warmup.WarmupConfig((), ("feature",), ("/project/scripts",))

        with (
            patch.object(warmup, "load_warmup_config", return_value=config),
            patch.object(warmup.importlib, "import_module", return_value=module),
        ):
            warmup.warmup()

        hook.assert_called_once_with()
        self.assertNotIn("/project/scripts", sys.path)

    def test_missing_prewarm_hook_does_not_abort_other_modules(self) -> None:
        missing_hook = ModuleType("missing_hook")
        valid_hook = ModuleType("valid_hook")
        valid_hook.prewarm = Mock()
        modules = {
            "missing_hook": missing_hook,
            "valid_hook": valid_hook,
        }
        config = warmup.WarmupConfig(
            (), ("missing_hook", "valid_hook"), ()
        )

        with (
            patch.object(warmup, "load_warmup_config", return_value=config),
            patch.object(
                warmup.importlib,
                "import_module",
                side_effect=lambda name: modules[name],
            ),
            self.assertLogs(level="ERROR"),
        ):
            warmup.warmup()

        valid_hook.prewarm.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
