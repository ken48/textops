from __future__ import annotations

import re

from .cleanup_options import CleanupMarkdownOptions
from .sentence_boundaries import (
    _abbreviation_dot_indices,
    _capitalize_sentences,
    _is_word_char,
)

QUOTE_NORMALIZATION = str.maketrans(
    {
        "«": '"',
        "»": '"',
        "„": '"',
        "“": '"',
        "”": '"',
        "‟": '"',
        "’": "'",
        "‘": "'",
        "‚": "'",
        "‛": "'",
    }
)
SPACE_BEFORE_PUNCT_RE = re.compile(r"\s+([,;:!?])")
SPACE_BEFORE_DOT_RE = re.compile(r"(?<!\d)\s+(\.)")
SPACE_AFTER_PUNCT_RE = re.compile(r"(?<!\d)([,;:!?]+)(?=[0-9A-Za-zА-Яа-яЁё])")
DASH_SEPARATOR_RE = re.compile(
    r"(?<=\S)(?:[ \t]*-(?!>)[ \t]+|[ \t]+-(?!>)[ \t]*|[ \t]*—[ \t]*)(?=\S)"
)
NUM_COLON_RE = re.compile(r"(\d)[ \t]*:[ \t]*(\d)")
MULTI_SPACE_RE = re.compile(r"[ \t]{2,}")
TECHNICAL_TOKEN_RE = re.compile(
    r"(?<!\S)("
    r"(?:https?|ftp)://[^\s<>()]+"
    r"|www\.[^\s<>()]+"
    r"|[^\s/@]+(?:\.[^\s/@]+)*@[^\s/@]+\.[^\s/@]+"
    r"|(?:~|/|\./|\.\./)\S*"
    r"|[A-Za-z]:\\\S*"
    r"|\.[^\s/]+(?:/\S*)?"
    r"|(?:[^\W_]+(?:-[^\W_]+)*\.){2,}[^\W_]{2,}"
    r")(?!\S)",
    re.UNICODE,
)


def _protect_technical_tokens(text: str) -> tuple[str, list[str]]:
    replacements: list[str] = []

    def replace(match: re.Match[str]) -> str:
        replacements.append(match.group(0))
        return f"\x00{len(replacements) - 1}\x00"

    return TECHNICAL_TOKEN_RE.sub(replace, text), replacements


def _restore_technical_tokens(text: str, replacements: list[str]) -> str:
    for index, original in enumerate(replacements):
        text = text.replace(f"\x00{index}\x00", original)
    return text


def _normalize_dot_spacing(text: str) -> str:
    abbreviation_dots = _abbreviation_dot_indices(text)
    result: list[str] = []

    for index, char in enumerate(text):
        result.append(char)
        if char != "." or index + 1 >= len(text) or index in abbreviation_dots:
            continue

        prev_char = text[index - 1] if index > 0 else ""
        next_char = text[index + 1]

        if next_char.isspace() or not _is_word_char(prev_char) or not next_char.isalpha():
            continue

        # "3.x"-style references: digit before the dot, single Latin letter after.
        # A Cyrillic letter or a longer word after the dot ("было 3.я ушел",
        # "было 3.потом") is a glued sentence start.
        if (
            prev_char.isdigit()
            and next_char.isascii()
            and (index + 2 >= len(text) or not text[index + 2].isalpha())
        ):
            continue

        result.append(" ")

    return "".join(result)


def _normalize_fragment_spacing(text: str, options: CleanupMarkdownOptions) -> str:
    if options.normalize_quotes:
        text = text.translate(QUOTE_NORMALIZATION)
    if options.normalize_dashes:
        text = DASH_SEPARATOR_RE.sub(" — ", text)
    if options.normalize_time_ranges:
        text = NUM_COLON_RE.sub(r"\1:\2", text)
    if options.normalize_punctuation_spacing:
        text = SPACE_BEFORE_PUNCT_RE.sub(r"\1", text)
        text = SPACE_BEFORE_DOT_RE.sub(r"\1", text)
        text = SPACE_AFTER_PUNCT_RE.sub(r"\1 ", text)
    if options.normalize_sentence_dot_spacing:
        text = _normalize_dot_spacing(text)
    if options.collapse_inline_whitespace:
        text = MULTI_SPACE_RE.sub(" ", text)
    return text


def _format_prose_fragment(
    text: str,
    *,
    sentence_start: bool,
    options: CleanupMarkdownOptions,
) -> tuple[str, bool]:
    replacements: list[str] = []
    if options.preserve_technical_tokens:
        text, replacements = _protect_technical_tokens(text)
    text = _normalize_fragment_spacing(text, options)
    should_capitalize = options.capitalize_sentences
    if should_capitalize and not sentence_start:
        text = re.sub(
            r'^([.!?]\s+)([A-Za-zА-Яа-яЁё])',
            lambda match: match.group(1) + match.group(2).upper(),
            text,
            count=1,
        )
    if should_capitalize:
        text, sentence_start = _capitalize_sentences(text, sentence_start)
    else:
        _, sentence_start = _capitalize_sentences(text, sentence_start)
    if options.preserve_technical_tokens:
        text = _restore_technical_tokens(text, replacements)
    return text, sentence_start
