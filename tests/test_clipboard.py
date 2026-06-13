from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

try:
    from core import clipboard
except ModuleNotFoundError as exc:
    if exc.name != "AppKit":
        raise
    clipboard = None
    HAS_APPKIT = False
else:
    HAS_APPKIT = sys.platform == "darwin"


class _FakePasteboard:
    def __init__(
        self,
        counts: list[int],
        values: list[str | None],
        has_string_type: bool = True,
    ) -> None:
        self._counts = counts
        self._values = values
        self._has_string_type = has_string_type
        self._count_index = 0
        self._value_index = 0

    def changeCount(self) -> int:
        index = min(self._count_index, len(self._counts) - 1)
        value = self._counts[index]
        self._count_index += 1
        return value

    def availableTypeFromArray_(self, _types: object) -> object | None:
        return clipboard.NSPasteboardTypeString if self._has_string_type else None

    def stringForType_(self, _type: object) -> str | None:
        index = min(self._value_index, len(self._values) - 1)
        value = self._values[index]
        self._value_index += 1
        return value


class _FakeNSPasteboard:
    def __init__(self, pasteboard: _FakePasteboard) -> None:
        self._pasteboard = pasteboard

    def generalPasteboard(self) -> _FakePasteboard:
        return self._pasteboard


class _FakeMonotonic:
    def __init__(self, values: list[float]) -> None:
        self._values = values
        self._index = 0

    def __call__(self) -> float:
        index = min(self._index, len(self._values) - 1)
        value = self._values[index]
        self._index += 1
        return value


def _patched(pasteboard: _FakePasteboard, monotonic: _FakeMonotonic):
    return (
        patch.object(clipboard, "NSPasteboard", new=_FakeNSPasteboard(pasteboard)),
        patch.object(clipboard.time, "monotonic", new=monotonic),
        patch.object(clipboard.time, "sleep", return_value=None),
    )


@unittest.skipUnless(HAS_APPKIT, "requires macOS AppKit")
class WaitForClipboardChangeTests(unittest.TestCase):
    def test_text_immediately_present(self) -> None:
        pasteboard = _FakePasteboard(counts=[10, 11], values=["selected text"])
        monotonic = _FakeMonotonic([0.0, 0.1, 0.2])
        p_pb, p_mono, p_sleep = _patched(pasteboard, monotonic)

        with p_pb, p_mono, p_sleep:
            self.assertEqual(
                clipboard.wait_for_clipboard_change(previous_count=10, timeout=0.5),
                "selected text",
            )

    def test_waits_full_timeout_for_a_slow_text_publisher(self) -> None:
        # changeCount advances and a string type is declared, but the value is
        # materialized late (well after any short grace would have expired). As
        # long as it lands before the outer timeout, we must still return it.
        pasteboard = _FakePasteboard(
            counts=[11],
            values=[None, None, "slow text"],
            has_string_type=True,
        )
        monotonic = _FakeMonotonic([0.0, 0.1, 0.3, 0.45])
        p_pb, p_mono, p_sleep = _patched(pasteboard, monotonic)

        with p_pb, p_mono, p_sleep:
            self.assertEqual(
                clipboard.wait_for_clipboard_change(previous_count=10, timeout=0.5),
                "slow text",
            )

    def test_returns_none_immediately_for_non_text_clipboard(self) -> None:
        # changeCount advanced but no string type is present (an image). We bail
        # out at once — the huge timeout proves we never poll/wait for it.
        pasteboard = _FakePasteboard(
            counts=[11],
            values=[None],
            has_string_type=False,
        )
        monotonic = _FakeMonotonic([0.0, 0.1])
        p_pb, p_mono, p_sleep = _patched(pasteboard, monotonic)

        with p_pb, p_mono, p_sleep:
            self.assertIsNone(
                clipboard.wait_for_clipboard_change(previous_count=10, timeout=10.0),
            )

    def test_returns_none_when_clipboard_never_changes(self) -> None:
        pasteboard = _FakePasteboard(counts=[10, 10, 10], values=[None])
        monotonic = _FakeMonotonic([0.0, 0.1, 0.2, 0.6])
        p_pb, p_mono, p_sleep = _patched(pasteboard, monotonic)

        with p_pb, p_mono, p_sleep:
            self.assertIsNone(
                clipboard.wait_for_clipboard_change(previous_count=10, timeout=0.5),
            )


if __name__ == "__main__":
    unittest.main()
