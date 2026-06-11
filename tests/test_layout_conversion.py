import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from transforms.layout_conversion import (
    LayoutConversionDirection,
    replace_last_layout_mismatched_sequence,
)

# Small QWERTY -> ЙЦУКЕН subset; the conversion logic does not depend on the
# full production map, which lives in scripts/auto_layout_fixer.py.
LAYOUT_A_TO_B = {
    'b': 'и',
    'd': 'в',
    'e': 'у',
    'f': 'а',
    'g': 'п',
    'h': 'р',
    'k': 'л',
    'l': 'д',
    'n': 'т',
    'o': 'з',
    'r': 'к',
    't': 'е',
}

MAX_CHARS = 24
TEST_CHARS = 3


def convert(text: str, max_chars: int = MAX_CHARS):
    return replace_last_layout_mismatched_sequence(
        text, LAYOUT_A_TO_B, max_chars, TEST_CHARS
    )


class ReplaceLastLayoutMismatchedSequenceTests(unittest.TestCase):
    def test_converts_english_layout_word_to_russian(self) -> None:
        self.assertEqual(
            convert("ghbdtn"),
            ("привет", LayoutConversionDirection.B),
        )

    def test_converts_russian_layout_word_to_english(self) -> None:
        self.assertEqual(
            convert("руддз"),
            ("hello", LayoutConversionDirection.A),
        )

    def test_converts_only_last_word_and_keeps_prefix(self) -> None:
        self.assertEqual(
            convert("hello ghbdtn"),
            ("hello привет", LayoutConversionDirection.B),
        )

    def test_preserves_trailing_whitespace(self) -> None:
        self.assertEqual(
            convert("ghbdtn \n"),
            ("привет \n", LayoutConversionDirection.B),
        )

    def test_converts_word_longer_than_old_window_in_full(self) -> None:
        self.assertEqual(
            convert("ghbdtnrfrltkf"),
            ("приветкакдела", LayoutConversionDirection.B),
        )

    def test_never_partially_converts_word_longer_than_limit(self) -> None:
        text = "ghbdtnrfrltkf"

        self.assertEqual(
            convert(text, max_chars=12),
            (text, LayoutConversionDirection.UNDEFINED),
        )

    def test_keeps_whitespace_only_text_unchanged(self) -> None:
        self.assertEqual(
            convert("  \n "),
            ("  \n ", LayoutConversionDirection.UNDEFINED),
        )

    def test_keeps_empty_text_unchanged(self) -> None:
        self.assertEqual(
            convert(""),
            ("", LayoutConversionDirection.UNDEFINED),
        )


if __name__ == "__main__":
    unittest.main()
