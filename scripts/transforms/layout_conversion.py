import re
from enum import IntEnum


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
    if not text or text.isspace():
        return text, LayoutConversionDirection.UNDEFINED

    last_part = text[-max_chars:] if len(text) > max_chars else text
    matches = list(re.finditer(r'\S+', last_part))
    if not matches:
        return text, LayoutConversionDirection.UNDEFINED

    start, end = matches[-1].span()
    word = last_part[start:end]
    converted_word, direction = _convert_text_and_detect_direction(
        word,
        word[-test_chars:],
        layout_a_to_b,
    )

    if converted_word == word:
        return text, direction

    new_last_part = last_part[:start] + converted_word + last_part[end:]
    prefix = text[:-len(last_part)] if len(last_part) < len(text) else ''
    return prefix + new_last_part, direction
