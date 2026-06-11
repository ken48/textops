import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "warmpy"))

from host.socket_server import SocketServer


def parse(payload_text: str):
    return SocketServer(worker=None)._parse_request(payload_text)


class ParseRequestTests(unittest.TestCase):
    def test_parses_full_json_payload(self) -> None:
        payload = (
            '{"script": "/tmp/run.py", "args": ["--select-all"],'
            ' "clean": true, "clean_root": "/tmp/project"}'
        )

        self.assertEqual(
            parse(payload),
            ("/tmp/run.py", ["--select-all"], True, "/tmp/project"),
        )

    def test_defaults_optional_json_fields(self) -> None:
        self.assertEqual(
            parse('{"script": "/tmp/run.py"}'),
            ("/tmp/run.py", [], False, None),
        )

    def test_treats_non_object_json_as_legacy_payload(self) -> None:
        # Only "{"-prefixed payloads are parsed as JSON; anything else falls back
        # to the legacy NUL-separated format and is later rejected by the worker.
        self.assertEqual(
            parse('["not", "an", "object"]'),
            ('["not", "an", "object"]', [], False, None),
        )

    def test_rejects_malformed_json(self) -> None:
        self.assertIsNone(parse('{"script": '))

    def test_rejects_non_list_args(self) -> None:
        self.assertIsNone(parse('{"script": "/tmp/run.py", "args": "oops"}'))

    def test_rejects_non_bool_clean(self) -> None:
        self.assertIsNone(parse('{"script": "/tmp/run.py", "clean": "yes"}'))

    def test_rejects_non_string_clean_root(self) -> None:
        self.assertIsNone(parse('{"script": "/tmp/run.py", "clean_root": 1}'))

    def test_parses_legacy_nul_separated_payload(self) -> None:
        self.assertEqual(
            parse("/tmp/run.py\x00--select-all\x00\x00extra"),
            ("/tmp/run.py", ["--select-all", "extra"], False, None),
        )


if __name__ == "__main__":
    unittest.main()
