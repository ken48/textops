from __future__ import annotations

import re

CLOSING_PUNCTUATION_CHARS = "\"')]}"

# Dotted abbreviations of 1-2 letter groups: "т.н.", "т.е.", "и т.д.", "e.g.", "p.s."
ABBREVIATION_RE = re.compile(r"(?<![\w.])(?:[^\W\d_]{1,2}\.){2,}(?!\w)")
# Common single-word abbreviations whose trailing dot does not end a sentence.
ABBREVIATION_WORD_RE = re.compile(
    r"(?<![\w.])(?:"
    r"см|ср|др|пр|стр|гл|рис|табл|прим|напр|тыс|млн|млрд|руб|англ|лат"
    r"|etc|vs|fig|approx"
    r")\.(?!\w)",
    re.IGNORECASE,
)
# Abbreviations normally followed by a capitalized proper noun ("ул. Ленина",
# "Mr. Brown"): a capital after them never signals a new sentence.
NAME_PREFIX_ABBREVIATION_RE = re.compile(
    r"(?<![\w.])(?:им|ул|ст|mr|mrs|ms|dr|st)\.(?!\w)",
    re.IGNORECASE,
)


def _is_word_char(char: str) -> bool:
    return char.isalnum() or char == "_"


def _next_non_space(text: str, start: int) -> tuple[int, str]:
    for index in range(start, len(text)):
        if not text[index].isspace():
            return index, text[index]
    return -1, ""


def _previous_sentence_char(text: str, start: int) -> str:
    for index in range(start, -1, -1):
        char = text[index]
        if char in CLOSING_PUNCTUATION_CHARS or char.isspace():
            continue
        return char
    return ""


def _next_after_closing_punctuation(text: str, start: int) -> tuple[int, str]:
    index = start
    while index < len(text) and text[index] in CLOSING_PUNCTUATION_CHARS:
        index += 1
    return _next_non_space(text, index)


def _starts_capitalized_word(text: str, start: int) -> bool:
    _, next_char = _next_non_space(text, start)
    return next_char.isalpha() and next_char.isupper()


def _abbreviation_dot_indices(text: str) -> set[int]:
    """Dots inside abbreviations that must not be treated as sentence boundaries.

    The final dot of an abbreviation may still end the sentence: when the next
    word is already capitalized, it is kept as a boundary. Name prefixes are the
    exception: a capital after "ул."/"Mr." is a proper noun, not a new sentence.
    """
    indices: set[int] = set()

    for match in NAME_PREFIX_ABBREVIATION_RE.finditer(text):
        indices.add(match.end() - 1)

    matches = list(ABBREVIATION_RE.finditer(text))
    matches += ABBREVIATION_WORD_RE.finditer(text)
    for match in matches:
        for index in range(match.start(), match.end()):
            if text[index] != ".":
                continue
            if index == match.end() - 1 and _starts_capitalized_word(text, index + 1):
                continue
            indices.add(index)

    return indices


def _is_sentence_boundary(text: str, index: int, abbreviation_dots: set[int]) -> bool:
    char = text[index]
    if char not in ".!?":
        return False

    if index in abbreviation_dots:
        return False

    next_char = text[index + 1] if index + 1 < len(text) else ""

    if char == "." and (
        not _is_word_char(_previous_sentence_char(text, index - 1))
        or _is_word_char(next_char)
    ):
        return False

    if next_char in CLOSING_PUNCTUATION_CHARS:
        _, after_closing_char = _next_after_closing_punctuation(text, index + 1)
        if (
            after_closing_char
            and after_closing_char.isalpha()
            and after_closing_char.islower()
        ):
            return False

    return True


def _capitalize_sentences(text: str, sentence_start: bool) -> tuple[str, bool]:
    abbreviation_dots = _abbreviation_dot_indices(text)
    result: list[str] = []

    for index, char in enumerate(text):
        if sentence_start and char.isalpha():
            result.append(char.upper())
            sentence_start = False
            continue

        result.append(char)

        if _is_sentence_boundary(text, index, abbreviation_dots):
            sentence_start = True
        elif not char.isspace() and char not in "\"'()[]{}":
            sentence_start = False

    return "".join(result), sentence_start


def _count_sentence_boundaries(text: str) -> int:
    stripped = text.strip()
    if not stripped:
        return 0

    abbreviation_dots = _abbreviation_dot_indices(stripped)
    return sum(
        1
        for index in range(len(stripped))
        if _is_sentence_boundary(stripped, index, abbreviation_dots)
    )
