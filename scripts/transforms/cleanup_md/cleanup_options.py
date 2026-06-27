from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CleanupMarkdownOptions:
    """Toggles for markdown prose cleanup."""

    normalize_quotes: bool = True
    normalize_dashes: bool = True
    normalize_time_ranges: bool = True
    normalize_punctuation_spacing: bool = True
    normalize_sentence_dot_spacing: bool = True
    collapse_inline_whitespace: bool = True
    capitalize_sentences: bool = True
    preserve_technical_tokens: bool = True
    preserve_tight_lists: bool = True
    strip_hardbreak_markup: bool = True
    normalize_bold_headings: bool = True
    restore_obsidian_wikilinks: bool = True
