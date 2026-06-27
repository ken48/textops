import re
from enum import IntEnum

LAST_WORD_RE = re.compile(r'(\S+)\s*\Z')


class LayoutConversionDirection(IntEnum):
    A = -1
    UNDEFINED = 0
    B = 1


def _convert_text_and_detect_direction(
    text: str,
    test_text: str,
    layout_a_to_b: dict[str, str],
) -> tuple[str, LayoutConversionDirection]:
    layout_b_to_a = {value: key for key, value in layout_a_to_b.items()}
    layout_a_chars = sum(1 for char in test_text if char in layout_a_to_b)
    layout_b_chars = sum(1 for char in test_text if char in layout_b_to_a)

    if layout_a_chars > layout_b_chars:
        return ''.join(layout_a_to_b.get(char, char) for char in text), LayoutConversionDirection.B

    if layout_b_chars > layout_a_chars:
        return ''.join(layout_b_to_a.get(char, char) for char in text), LayoutConversionDirection.A

    return text, LayoutConversionDirection.UNDEFINED


def replace_last_layout_mismatched_sequence(
    text: str,
    layout_a_to_b: dict[str, str],
    max_chars: int,
    test_chars: int,
) -> tuple[str, LayoutConversionDirection]:
    """Convert the last whitespace-delimited word of ``text`` to the opposite layout.

    The word is always matched in full: words longer than ``max_chars`` are left
    untouched rather than partially converted.
    """
    if not text or text.isspace():
        return text, LayoutConversionDirection.UNDEFINED

    match = LAST_WORD_RE.search(text)
    if match is None:
        return text, LayoutConversionDirection.UNDEFINED

    word = match.group(1)
    if len(word) > max_chars:
        return text, LayoutConversionDirection.UNDEFINED

    converted_word, direction = _convert_text_and_detect_direction(
        word,
        word[-test_chars:],
        layout_a_to_b,
    )

    if converted_word == word:
        return text, direction

    return text[:match.start(1)] + converted_word + text[match.end(1):], direction
